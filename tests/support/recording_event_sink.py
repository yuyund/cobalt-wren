"""In-memory EventSink test double."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from langgraph_automation.integrations.observability.types import SpanRef


@dataclass(slots=True)
class RecordedSpan:
    span_id: str
    run_id: int
    span_type: str
    name: str
    node_name: str = ""
    parent_id: str | None = None
    status: str = "running"
    output_summary: str = ""
    error_message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    started_metadata: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RecordedEvent:
    run_id: int
    kind: str
    message: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    node_name: str = ""


class RecordingEventSink:
    """Small in-memory sink for unit tests."""

    def __init__(self) -> None:
        self.run_events: list[RecordedEvent] = []
        self.spans: dict[str, RecordedSpan] = {}
        self._counter = 0

    def _next_span_id(self) -> str:
        self._counter += 1
        return f"span-{self._counter}"

    def _record_event(self, run_id: int, kind: str, message: str = "", payload: Mapping[str, Any] | None = None, node_name: str = "") -> RecordedEvent:
        event = RecordedEvent(run_id=run_id, kind=kind, message=message, payload=dict(payload or {}), node_name=node_name)
        self.run_events.append(event)
        return event

    def run_started(self, run_id: int, message: str | None = None, payload: Mapping[str, Any] | None = None) -> RecordedEvent:
        return self._record_event(run_id, "run.started", message or "", payload)

    def run_completed(self, run_id: int, message: str | None = None, payload: Mapping[str, Any] | None = None) -> RecordedEvent:
        return self._record_event(run_id, "run.completed", message or "", payload)

    def run_failed(self, run_id: int, error_message: str, payload: Mapping[str, Any] | None = None) -> RecordedEvent:
        return self._record_event(run_id, "run.failed", error_message, payload)

    def run_cancelled(self, run_id: int, message: str | None = None, payload: Mapping[str, Any] | None = None) -> RecordedEvent:
        return self._record_event(run_id, "run.cancelled", message or "", payload)

    def semantic_event(self, run_id: int, name: str, message: str | None = None, payload: Mapping[str, Any] | None = None, level: str = "info", parent_span: SpanRef | None = None, node_name: str | None = None) -> RecordedEvent:
        return self._record_event(run_id, name, message or name, payload, node_name=node_name or "")

    def span_started(self, run_id: int, span_type: str, name: str, node_name: str | None = None, parent: SpanRef | None = None, metadata: Mapping[str, Any] | None = None) -> SpanRef:
        span_id = self._next_span_id()
        start_metadata = dict(metadata or {})
        self.spans[span_id] = RecordedSpan(
            span_id=span_id,
            run_id=run_id,
            span_type=span_type,
            name=name,
            node_name=node_name or "",
            parent_id=None if parent is None else parent.span_id,
            metadata=start_metadata,
            started_metadata=start_metadata,
        )
        return SpanRef(span_id=span_id)

    def span_completed(self, span: SpanRef, output_summary: str | None = None, metrics: Mapping[str, Any] | None = None, metadata: Mapping[str, Any] | None = None) -> RecordedSpan:
        record = self.spans[span.span_id]
        record.status = "succeeded"
        record.output_summary = output_summary or ""
        record.metrics = dict(metrics or {})
        if metadata is not None:
            record.metadata = dict(metadata)
        return record

    def span_failed(self, span: SpanRef, error_message: str, metrics: Mapping[str, Any] | None = None, metadata: Mapping[str, Any] | None = None) -> RecordedSpan:
        record = self.spans[span.span_id]
        record.status = "failed"
        record.error_message = error_message
        record.metrics = dict(metrics or {})
        if metadata is not None:
            record.metadata = dict(metadata)
        return record

    def node_started(self, run_id: int, node_name: str, attempt: int = 1, parent: SpanRef | None = None) -> SpanRef:
        return self.span_started(run_id, "node", node_name, node_name=node_name, parent=parent, metadata={"attempt": attempt})

    def node_completed(self, span: SpanRef, output_summary: str | None = None, metrics: Mapping[str, Any] | None = None) -> RecordedSpan:
        return self.span_completed(span, output_summary=output_summary, metrics=metrics)

    def node_failed(self, span: SpanRef, error_message: str, metrics: Mapping[str, Any] | None = None) -> RecordedSpan:
        return self.span_failed(span, error_message=error_message, metrics=metrics)

    def llm_started(self, run_id: int, name: str, node_name: str | None = None, parent: SpanRef | None = None, provider: str | None = None, model: str | None = None) -> SpanRef:
        return self.span_started(run_id, "llm", name, node_name=node_name, parent=parent, metadata={"provider": provider, "model": model})

    def llm_completed(self, span: SpanRef, output_summary: str | None = None, metrics: Mapping[str, Any] | None = None) -> RecordedSpan:
        return self.span_completed(span, output_summary=output_summary, metrics=metrics)

    def llm_failed(self, span: SpanRef, error_message: str, metrics: Mapping[str, Any] | None = None) -> RecordedSpan:
        return self.span_failed(span, error_message=error_message, metrics=metrics)

    def tool_started(self, run_id: int, tool_name: str, node_name: str | None = None, parent: SpanRef | None = None) -> SpanRef:
        return self.span_started(run_id, "tool", tool_name, node_name=node_name, parent=parent)

    def tool_completed(self, span: SpanRef, output_summary: str | None = None, metrics: Mapping[str, Any] | None = None) -> RecordedSpan:
        return self.span_completed(span, output_summary=output_summary, metrics=metrics)

    def tool_failed(self, span: SpanRef, error_message: str, metrics: Mapping[str, Any] | None = None) -> RecordedSpan:
        return self.span_failed(span, error_message=error_message, metrics=metrics)

    def artifact_created(self, run_id: int, storage_key: str, name: str, kind: str, span: SpanRef | None = None, metadata: Mapping[str, Any] | None = None, content_type: str = '', size: int | None = None) -> RecordedEvent:
        payload = dict(metadata or {})
        payload.update({"content_type": content_type, "size": size})
        return self._record_event(run_id, "artifact.created", storage_key, payload, node_name=name)

    def checkpoint_saved(self, run_id: int, thread_id: str, checkpoint_id: str, backend: str, span: SpanRef | None = None, state_summary: str | None = None, checkpoint_namespace: str = '') -> RecordedEvent:
        return self._record_event(run_id, "checkpoint.saved", checkpoint_id, {"thread_id": thread_id, "backend": backend, "state_summary": state_summary or "", "checkpoint_namespace": checkpoint_namespace})
