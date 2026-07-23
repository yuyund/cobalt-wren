"""Public workflow vocabulary facade for langgraph-automation."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable
import time

from .errors import WorkflowCancelledError, WorkflowTimeoutError

__all__ = [
    "WorkflowBuildContext",
    "WorkflowExecutionContext",
    "WorkflowExecutionControl",
    "WorkflowResumeRequest",
    "WorkflowExecutionResult",
    "WorkflowExecutable",
    "WorkflowResumable",
    "WorkflowMetadata",
    "WorkflowRequirements",
    "WorkflowDefinition",
    "WorkflowContribution",
]


def _copy_mapping(mapping: Mapping[str, Any] | None) -> dict[str, Any]:
    return dict(mapping or {})


def _tupleize_strs(values: object) -> tuple[str, ...]:
    if isinstance(values, tuple):
        return values
    return tuple(values)  # type: ignore[arg-type]


@dataclass(frozen=True, slots=True)
class WorkflowBuildContext:
    """Public, framework-neutral dependencies supplied to a workflow builder."""

    workflow_kind: str
    config: Mapping[str, object] = field(default_factory=dict)
    providers: Mapping[str, object] = field(default_factory=dict)
    tools: Mapping[str, object] = field(default_factory=dict)
    artifact_store: object | None = None
    checkpoint_store: object | None = None
    event_sinks: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "config", _copy_mapping(self.config))
        object.__setattr__(self, "providers", _copy_mapping(self.providers))
        object.__setattr__(self, "tools", _copy_mapping(self.tools))
        object.__setattr__(self, "event_sinks", _copy_mapping(self.event_sinks))

    def require_provider(self, profile_name: str) -> object:
        try:
            return self.providers[profile_name]
        except KeyError as exc:
            raise LookupError(f"provider profile {profile_name!r} is unavailable") from exc

    def require_tool(self, tool_name: str) -> object:
        try:
            return self.tools[tool_name]
        except KeyError as exc:
            raise LookupError(f"tool {tool_name!r} is unavailable") from exc

    def require_artifact_store(self) -> object:
        if self.artifact_store is None:
            raise LookupError("artifact store is unavailable")
        return self.artifact_store

    def require_checkpoint_store(self) -> object:
        if self.checkpoint_store is None:
            raise LookupError("checkpoint store is unavailable")
        return self.checkpoint_store

    def require_event_sink(self, sink_name: str) -> object:
        try:
            return self.event_sinks[sink_name]
        except KeyError as exc:
            raise LookupError(f"event sink {sink_name!r} is unavailable") from exc


@dataclass(frozen=True, slots=True)
class WorkflowExecutionControl:
    """Framework-neutral cooperative cancellation and deadline token."""

    cancellation_requested: Callable[[], bool]
    deadline_monotonic: float | None = None

    @property
    def is_cancelled(self) -> bool:
        return bool(self.cancellation_requested())

    @property
    def remaining_seconds(self) -> float | None:
        if self.deadline_monotonic is None:
            return None
        return max(0.0, self.deadline_monotonic - time.monotonic())

    def check(self) -> None:
        if self.is_cancelled:
            raise WorkflowCancelledError()
        if self.deadline_monotonic is not None and time.monotonic() >= self.deadline_monotonic:
            raise WorkflowTimeoutError()


@dataclass(frozen=True, slots=True)
class WorkflowExecutionContext:
    """Per-run context supplied when a workflow executes or resumes."""

    run_id: int | None = None
    thread_id: str = ""
    event_sink: object | None = None
    parent_span: object | None = None
    control: WorkflowExecutionControl | None = None


@dataclass(frozen=True, slots=True)
class WorkflowResumeRequest:
    """Framework-neutral input used to continue a paused workflow."""

    value: Mapping[str, object] = field(default_factory=dict)
    checkpoint_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _copy_mapping(self.value))
        if self.checkpoint_id is not None:
            normalized = self.checkpoint_id.strip()
            if not normalized:
                raise ValueError("checkpoint_id must not be blank")
            object.__setattr__(self, "checkpoint_id", normalized)


@dataclass(frozen=True, slots=True)
class WorkflowExecutionResult:
    """Framework-neutral normalized workflow execution result."""

    output: Mapping[str, object] = field(default_factory=dict)
    metadata: Mapping[str, object] = field(default_factory=dict)
    status: str = "completed"

    def __post_init__(self) -> None:
        object.__setattr__(self, "output", _copy_mapping(self.output))
        object.__setattr__(self, "metadata", _copy_mapping(self.metadata))
        if self.status not in {"completed", "paused"}:
            raise ValueError("workflow execution status must be 'completed' or 'paused'")


@runtime_checkable
class WorkflowExecutable(Protocol):
    def execute(
        self,
        input_payload: Mapping[str, object],
        *,
        context: WorkflowExecutionContext,
    ) -> object: ...


@runtime_checkable
class WorkflowResumable(Protocol):
    def resume(
        self,
        request: WorkflowResumeRequest,
        *,
        context: WorkflowExecutionContext,
    ) -> object: ...


@dataclass(frozen=True, slots=True)
class WorkflowMetadata:
    name: str
    description: str = ""
    version: str = "0.1.0"
    tags: tuple[str, ...] = ()
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "tags", _tupleize_strs(self.tags))
        object.__setattr__(self, "metadata", _copy_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class WorkflowRequirements:
    provider_profiles: tuple[str, ...] = ()
    tools: tuple[str, ...] = ()
    artifact_store: bool = False
    checkpoint_store: bool = False
    event_sinks: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "provider_profiles", _tupleize_strs(self.provider_profiles))
        object.__setattr__(self, "tools", _tupleize_strs(self.tools))
        object.__setattr__(self, "event_sinks", _tupleize_strs(self.event_sinks))


@dataclass(frozen=True, slots=True)
class WorkflowDefinition:
    kind: str
    metadata: WorkflowMetadata
    requirements: WorkflowRequirements
    build: Callable[..., object]
    input_schema: Mapping[str, object] | None = None
    output_schema: Mapping[str, object] | None = None
    extra: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "input_schema", None if self.input_schema is None else _copy_mapping(self.input_schema))
        object.__setattr__(self, "output_schema", None if self.output_schema is None else _copy_mapping(self.output_schema))
        object.__setattr__(self, "extra", _copy_mapping(self.extra))


@dataclass(frozen=True, slots=True)
class WorkflowContribution:
    kind: str
    definition: WorkflowDefinition
    validate_config: Callable[..., None] | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", _copy_mapping(self.metadata))
