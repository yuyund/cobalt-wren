"""Convenience facades exposed by ``NativeWorkflowContext``."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
import json
import re
from types import MappingProxyType
from typing import Any, TYPE_CHECKING, cast

from cobalt_wren.api.stores import ArtifactStore, ArtifactWriteRequest, StoredArtifact
from cobalt_wren.core.redaction import redact_mapping
from cobalt_wren.integrations.artifact.emission import (
    ArtifactEmissionContext,
    ArtifactEmissionRequest,
    build_artifact_identity,
    build_artifact_storage_key,
)
from cobalt_wren.integrations.llm.base import LLMClient, LLMRequest, LLMResult
from cobalt_wren.integrations.llm.observed_client import ObservedLLMClient
from cobalt_wren.integrations.observability.base import EventSink
from cobalt_wren.integrations.observability.failure_policy import suppress_observability_failure
from cobalt_wren.integrations.observability.types import ObservabilityContext, SpanRef
from cobalt_wren.integrations.tools.base import ToolCallable, ToolResult
from cobalt_wren.integrations.tools.observed_registry import ObservedToolRegistry
from cobalt_wren.integrations.tools.registry import InMemoryToolRegistry
from cobalt_wren.native.policies import RetryPolicy

if TYPE_CHECKING:
    from cobalt_wren.native import NativeWorkflowContext

_SAFE_ARTIFACT_NAME = re.compile(r"^[^/\\\x00]{1,255}$")
_ARTIFACT_SLOT_UNSAFE = re.compile(r"[^a-z0-9]+")


def _validate_artifact_name(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("artifact name must be a string")
    normalized = value.strip()
    if normalized != value or not normalized:
        raise ValueError("artifact name must not be blank or contain surrounding whitespace")
    if not _SAFE_ARTIFACT_NAME.fullmatch(normalized):
        raise ValueError("artifact name must not contain path separators or NUL bytes")
    return normalized


def _artifact_slot(name: str) -> str:
    stem = name.rsplit(".", 1)[0].strip().lower()
    normalized = _ARTIFACT_SLOT_UNSAFE.sub("-", stem).strip("-")
    return normalized or "artifact"


def _serialize_artifact_content(content: object) -> tuple[bytes, str]:
    if isinstance(content, bytes):
        return content, "application/octet-stream"
    if isinstance(content, str):
        return content.encode("utf-8"), "text/plain; charset=utf-8"
    if isinstance(content, Mapping) or (
        isinstance(content, Sequence)
        and not isinstance(content, (str, bytes, bytearray))
    ):
        rendered = json.dumps(
            content,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return rendered.encode("utf-8"), "application/json"
    raise TypeError("artifact content must be bytes, text, a mapping, or a sequence")


def _freeze_value(value: object) -> object:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze_value(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze_value(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_freeze_value(item) for item in value)
    return value


@dataclass(frozen=True, slots=True)
class NativeArtifact:
    storage_key: str
    name: str
    kind: str
    content_type: str | None
    size: int
    digest: str
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        safe_metadata = redact_mapping(dict(self.metadata))
        object.__setattr__(
            self,
            "metadata",
            cast(Mapping[str, object], _freeze_value(safe_metadata)),
        )


@dataclass(frozen=True, slots=True)
class NativeArtifactHelper:
    context: "NativeWorkflowContext"

    async def write(
        self,
        *,
        name: str,
        content: object,
        kind: str = "file",
        content_type: str | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> NativeArtifact:
        run_id = self.context.execution.run_id
        if isinstance(run_id, bool) or not isinstance(run_id, int) or run_id <= 0:
            raise RuntimeError("Native artifact writing requires a positive integer Run identity")
        artifact_name = _validate_artifact_name(name)
        body, default_content_type = _serialize_artifact_content(content)
        effective_content_type = content_type or default_content_type
        author_metadata = dict(metadata or {})
        emission = ArtifactEmissionRequest(
            slot=_artifact_slot(artifact_name),
            body=body,
            content_type=effective_content_type,
            metadata=author_metadata,
        )
        identity = build_artifact_identity(
            context=ArtifactEmissionContext(run_id=run_id),
            request=emission,
        )
        storage_key = build_artifact_storage_key(identity)
        store = cast(ArtifactStore, self.context.require_artifact_store())
        stored = await asyncio.to_thread(
            store.put,
            ArtifactWriteRequest(
                run_id=run_id,
                storage_key=storage_key,
                body=emission.body,
                name=artifact_name,
                kind=kind,
                content_type=emission.content_type,
                metadata=dict(emission.metadata),
            ),
        )
        self._emit_created(stored)
        return NativeArtifact(
            storage_key=stored.storage_key,
            name=stored.name,
            kind=stored.kind,
            content_type=stored.content_type,
            size=stored.size,
            digest=stored.digest,
            metadata=stored.metadata,
        )

    def _emit_created(self, artifact: StoredArtifact) -> None:
        sink = cast(EventSink | None, self.context.execution.event_sink)
        run_id = self.context.execution.run_id
        if sink is None or not isinstance(run_id, int):
            return
        span = cast(SpanRef | None, self.context.execution.parent_span)
        suppress_observability_failure(
            lambda: sink.artifact_created(
                run_id,
                artifact.storage_key,
                artifact.name,
                artifact.kind,
                span=span,
                metadata=artifact.metadata,
                content_type=artifact.content_type or "",
                size=artifact.size,
            ),
            context={
                "run_id": run_id,
                "storage_key": artifact.storage_key,
                "operation": "native.artifact.created",
            },
        )


@dataclass(frozen=True, slots=True)
class NativeLLMHelper:
    context: "NativeWorkflowContext"

    async def complete(
        self,
        step_name: str,
        messages: LLMRequest,
        *,
        profile: str = "default",
        retry: RetryPolicy | None = None,
        timeout_seconds: float | None = None,
        occurrence_key: str | None = None,
        **kwargs: Any,
    ) -> LLMResult:
        return await self.context.step(
            step_name,
            self._complete_sync,
            profile,
            tuple(dict(message) for message in messages),
            dict(kwargs),
            retry=retry,
            timeout_seconds=timeout_seconds,
            occurrence_key=occurrence_key,
        )

    def _complete_sync(
        self,
        profile: str,
        messages: Sequence[Mapping[str, Any]],
        kwargs: Mapping[str, Any],
    ) -> LLMResult:
        client = cast(LLMClient, self.context.require_provider(profile))
        observed = ObservedLLMClient(
            inner=client,
            event_sink=cast(EventSink | None, self.context.execution.event_sink),
            observability=_observability(self.context, "llm"),
        )
        return observed.complete(messages, **dict(kwargs))


@dataclass(frozen=True, slots=True)
class NativeToolHelper:
    context: "NativeWorkflowContext"

    async def run(
        self,
        step_name: str,
        tool_name: str,
        *,
        retry: RetryPolicy | None = None,
        timeout_seconds: float | None = None,
        occurrence_key: str | None = None,
        **kwargs: Any,
    ) -> ToolResult:
        return await self.context.step(
            step_name,
            self._run_sync,
            tool_name,
            dict(kwargs),
            retry=retry,
            timeout_seconds=timeout_seconds,
            occurrence_key=occurrence_key,
        )

    def _run_sync(self, tool_name: str, kwargs: Mapping[str, Any]) -> ToolResult:
        registry = InMemoryToolRegistry()
        registry.register(
            tool_name,
            cast(ToolCallable, self.context.require_tool(tool_name)),
        )
        observed = ObservedToolRegistry(
            inner=registry,
            event_sink=cast(EventSink | None, self.context.execution.event_sink),
            observability=_observability(self.context, "tool"),
        )
        return observed.run(tool_name, **dict(kwargs))


_EVENT_NAME = re.compile(r"^[a-z][a-z0-9_.-]{0,127}$")
_MAX_NATIVE_METRICS = 100


@dataclass(frozen=True, slots=True)
class NativeProgressHelper:
    context: "NativeWorkflowContext"

    async def update(
        self,
        *,
        current: int | float,
        total: int | float | None = None,
        message: str = "",
    ) -> None:
        if isinstance(current, bool) or not isinstance(current, (int, float)) or current < 0:
            raise ValueError("progress current must be a non-negative number")
        if total is not None and (
            isinstance(total, bool) or not isinstance(total, (int, float)) or total <= 0
        ):
            raise ValueError("progress total must be a positive number")
        if total is not None and current > total:
            raise ValueError("progress current must not exceed total")
        previous = self.context._progress_current
        if previous is not None and float(current) < previous:
            raise ValueError("progress current must be monotonic")
        established_total = self.context._progress_total
        if established_total is not None and total is not None and float(total) != established_total:
            raise ValueError("progress total must remain stable once reported")
        self.context._progress_current = float(current)
        if total is not None:
            self.context._progress_total = float(total)
        payload: dict[str, object] = {"current": current}
        if total is not None:
            payload["total"] = total
            payload["percent"] = round(float(current) / float(total) * 100, 2)
        _emit_semantic_event(self.context, "native.progress", message or "Progress updated", payload)


@dataclass(frozen=True, slots=True)
class NativeMetricHelper:
    context: "NativeWorkflowContext"

    def record(
        self,
        name: str,
        value: int | float,
        *,
        unit: str = "",
        metadata: Mapping[str, object] | None = None,
    ) -> None:
        import math

        if not _EVENT_NAME.fullmatch(name):
            raise ValueError("metric name must be a lowercase dotted identifier")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            raise ValueError("metric value must be a finite number")
        if name not in self.context._metric_names and len(self.context._metric_names) >= _MAX_NATIVE_METRICS:
            raise RuntimeError("Native workflow exceeded the distinct metric limit")
        self.context._metric_names.add(name)
        payload: dict[str, object] = {"name": name, "value": value, "aggregation": "latest"}
        if unit:
            payload["unit"] = unit
        if metadata:
            payload["metadata"] = redact_mapping(dict(metadata))
        _emit_semantic_event(self.context, "native.metric", f"Metric recorded: {name}", payload)


def _emit_semantic_event(
    context: "NativeWorkflowContext",
    name: str,
    message: str,
    payload: Mapping[str, object],
) -> None:
    sink = cast(EventSink | None, context.execution.event_sink)
    run_id = context.execution.run_id
    if sink is None or not isinstance(run_id, int):
        return
    suppress_observability_failure(
        lambda: sink.semantic_event(
            run_id,
            name,
            message=message,
            payload=payload,
            parent_span=cast(SpanRef | None, context.execution.parent_span),
            node_name="native",
        ),
        context={"component": "native", "operation": name, "run_id": run_id},
    )


def _observability(
    context: "NativeWorkflowContext",
    node_name: str,
) -> ObservabilityContext:
    return ObservabilityContext(
        run_id=context.execution.run_id if isinstance(context.execution.run_id, int) else None,
        thread_id=context.execution.thread_id,
        parent_span=cast(SpanRef | None, context.execution.parent_span),
        node_name=node_name,
    )


__all__ = ["NativeArtifact", "NativeArtifactHelper", "NativeLLMHelper", "NativeMetricHelper", "NativeProgressHelper", "NativeToolHelper"]
