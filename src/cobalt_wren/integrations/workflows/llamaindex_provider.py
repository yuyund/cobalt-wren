"""Official LlamaIndex Workflows integration provider.

The provider uses the public Workflow.run(), WorkflowHandler.stream_events(),
and StepStateChanged APIs. It does not inspect workflow or runtime private state.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Mapping
from concurrent.futures import Future
from dataclasses import dataclass, field
import json
from threading import Thread
from typing import Any, Coroutine, Protocol, TypeVar, cast

from workflows.events import (
    Event,
    InternalDispatchEvent,
    StepState,
    StepStateChanged,
    WorkflowFailedEvent,
)

from cobalt_wren.api.integrations import (
    IntegrationContext,
    IntegrationDefinition,
    WorkflowIntegrationProvider,
)
from cobalt_wren.api.workflow import (
    WorkflowExecutionContext,
    WorkflowExecutionResult,
)
from cobalt_wren.core.result_safety import safe_run_error_message
from cobalt_wren.core.summary import summarize_mapping
from cobalt_wren.integrations.observability.base import EventSink
from cobalt_wren.integrations.observability.failure_policy import (
    suppress_observability_failure,
)
from cobalt_wren.integrations.observability.types import SpanRef
from cobalt_wren.integrations.workflows.definitions import (
    LLAMAINDEX_WORKFLOWS_INTEGRATION,
)


class _WorkflowCapable(Protocol):
    @property
    def workflow_name(self) -> str: ...

    def run(self, **kwargs: object) -> object: ...


T = TypeVar("T")


class _BufferedObservationSink:
    """Collect sync sink calls while the workflow's async loop is running."""

    def __init__(self) -> None:
        self._counter = 0
        self._operations: list[tuple[str, dict[str, object]]] = []

    def span_started(
        self,
        run_id: int,
        span_type: str,
        name: str,
        node_name: str | None = None,
        parent: SpanRef | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> SpanRef:
        self._counter += 1
        ref = SpanRef(f"buffered-{self._counter}")
        self._operations.append(
            (
                "span_started",
                {
                    "ref": ref,
                    "run_id": run_id,
                    "span_type": span_type,
                    "name": name,
                    "node_name": node_name,
                    "parent": parent,
                    "metadata": dict(metadata or {}),
                },
            )
        )
        return ref

    def span_completed(
        self,
        span: SpanRef,
        output_summary: str | None = None,
        metrics: Mapping[str, object] | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> None:
        self._operations.append(
            (
                "span_completed",
                {
                    "span": span,
                    "output_summary": output_summary,
                    "metrics": dict(metrics or {}),
                    "metadata": dict(metadata or {}),
                },
            )
        )

    def span_failed(
        self,
        span: SpanRef,
        error_message: str,
        metrics: Mapping[str, object] | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> None:
        self._operations.append(
            (
                "span_failed",
                {
                    "span": span,
                    "error_message": error_message,
                    "metrics": dict(metrics or {}),
                    "metadata": dict(metadata or {}),
                },
            )
        )

    def integration_projection(
        self,
        run_id: int,
        *,
        integration_id: str,
        schema_id: str,
        owner_kind: str,
        payload: Mapping[str, object],
        span: SpanRef | None = None,
        owner_external_id: str = "",
        title: str = "",
        retention_class: str = "execution_detail",
        classification: str = "internal",
        projection_kind: str = "event",
        subject_kind: str = "run",
        subject_external_id: str = "",
        sequence: int = 0,
        occurred_at: object | None = None,
    ) -> None:
        self._operations.append(
            (
                "integration_projection",
                {
                    "run_id": run_id,
                    "integration_id": integration_id,
                    "schema_id": schema_id,
                    "owner_kind": owner_kind,
                    "payload": dict(payload),
                    "span": span,
                    "owner_external_id": owner_external_id,
                    "title": title,
                    "retention_class": retention_class,
                    "classification": classification,
                    "projection_kind": projection_kind,
                    "subject_kind": subject_kind,
                    "subject_external_id": subject_external_id,
                    "sequence": sequence,
                    "occurred_at": occurred_at,
                },
            )
        )

    def replay(self, sink: object | None) -> None:
        if sink is None:
            return
        typed_sink = cast(EventSink, sink)
        refs: dict[str, SpanRef] = {}
        for operation, data in self._operations:
            if operation == "span_started":
                buffered_ref = cast(SpanRef, data["ref"])
                parent = cast(SpanRef | None, data["parent"])
                resolved_parent = (
                    refs.get(parent.span_id, parent) if parent is not None else None
                )
                try:
                    real_ref = typed_sink.span_started(
                        cast(int, data["run_id"]),
                        span_type=cast(str, data["span_type"]),
                        name=cast(str, data["name"]),
                        node_name=cast(str | None, data["node_name"]),
                        parent=resolved_parent,
                        metadata=cast(Mapping[str, object], data["metadata"]),
                    )
                    refs[buffered_ref.span_id] = real_ref
                except Exception:
                    continue
            elif operation in {"span_completed", "span_failed"}:
                buffered_ref = cast(SpanRef, data["span"])
                terminal_ref = refs.get(buffered_ref.span_id)
                if terminal_ref is None:
                    continue
                try:
                    if operation == "span_completed":
                        typed_sink.span_completed(
                            terminal_ref,
                            output_summary=cast(str | None, data["output_summary"]),
                            metrics=cast(Mapping[str, object], data["metrics"]),
                            metadata=cast(Mapping[str, object], data["metadata"]),
                        )
                    else:
                        typed_sink.span_failed(
                            terminal_ref,
                            error_message=cast(str, data["error_message"]),
                            metrics=cast(Mapping[str, object], data["metrics"]),
                            metadata=cast(Mapping[str, object], data["metadata"]),
                        )
                except Exception:
                    continue
            elif operation == "integration_projection":
                callback = getattr(sink, "integration_projection", None)
                if not callable(callback):
                    continue
                buffered_span = cast(SpanRef | None, data["span"])
                real_span = (
                    refs.get(buffered_span.span_id)
                    if buffered_span is not None
                    else None
                )
                try:
                    callback(
                        cast(int, data["run_id"]),
                        integration_id=cast(str, data["integration_id"]),
                        schema_id=cast(str, data["schema_id"]),
                        owner_kind=cast(str, data["owner_kind"]),
                        payload=cast(Mapping[str, object], data["payload"]),
                        span=real_span,
                        owner_external_id=cast(str, data["owner_external_id"]),
                        title=cast(str, data["title"]),
                        retention_class=cast(str, data["retention_class"]),
                        classification=cast(str, data["classification"]),
                        projection_kind=cast(str, data["projection_kind"]),
                        subject_kind=cast(str, data["subject_kind"]),
                        subject_external_id=cast(str, data["subject_external_id"]),
                        sequence=cast(int, data["sequence"]),
                        occurred_at=data["occurred_at"],
                    )
                except Exception:
                    continue


@dataclass(slots=True)
class LlamaIndexWorkflowsExecutable:
    workflow: _WorkflowCapable
    workflow_kind: str
    run_kwargs: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.run_kwargs = dict(self.run_kwargs)

    def execute(
        self,
        input_payload: Mapping[str, object],
        *,
        context: WorkflowExecutionContext,
    ) -> WorkflowExecutionResult:
        real_sink = context.event_sink
        buffered_sink = _BufferedObservationSink()
        buffered_context = WorkflowExecutionContext(
            run_id=context.run_id,
            thread_id=context.thread_id,
            event_sink=buffered_sink,
            parent_span=context.parent_span,
            control=context.control,
        )
        try:
            return _run_awaitable(
                self._execute_async(dict(input_payload), context=buffered_context)
            )
        finally:
            buffered_sink.replay(real_sink)

    async def _execute_async(
        self,
        input_payload: dict[str, object],
        *,
        context: WorkflowExecutionContext,
    ) -> WorkflowExecutionResult:
        sink = cast(EventSink | None, context.event_sink)
        run_id = context.thread_id or str(context.run_id or self.workflow_kind)
        kwargs = {**dict(self.run_kwargs), **input_payload, "run_id": run_id}
        handler = self.workflow.run(**kwargs)
        stream_events = getattr(handler, "stream_events", None)
        if not callable(stream_events) or not hasattr(handler, "__await__"):
            raise TypeError(
                "LlamaIndex Workflows target must return an awaitable handler with stream_events()"
            )

        spans: dict[str, list[SpanRef]] = {}
        completed_steps: list[str] = []
        failed_steps: list[str] = []
        event_types: list[str] = []
        pending_terminals: list[tuple[str, SpanRef | None, dict[str, object]]] = []
        workflow_run_id = str(getattr(handler, "run_id", run_id))

        try:
            async for event in stream_events(expose_internal=True):
                if context.control is not None:
                    context.control.check()
                if isinstance(event, StepStateChanged):
                    _handle_step_state(
                        event,
                        sink=sink,
                        context=context,
                        workflow_run_id=workflow_run_id,
                        spans=spans,
                        pending_terminals=pending_terminals,
                    )
                    continue
                event_type = type(event).__name__
                event_types.append(event_type)
                _emit_projection(
                    sink,
                    context=context,
                    schema_id="llamaindex.event.v1",
                    owner_kind="run",
                    owner_external_id=f"{workflow_run_id}:{len(event_types)}",
                    title=f"LlamaIndex event: {event_type}",
                    payload={
                        "run_id": workflow_run_id,
                        "event_type": event_type,
                        "internal": isinstance(event, InternalDispatchEvent),
                        "summary": _event_summary(event),
                    },
                    projection_kind="event",
                    subject_kind="run",
                    subject_external_id=workflow_run_id,
                    sequence=len(event_types),
                )
                if isinstance(event, WorkflowFailedEvent):
                    failed_steps.append(event.step_name)
                    pending = _pop_pending_terminal(
                        event.step_name, pending_terminals
                    )
                    if pending is not None:
                        _, span, metadata = pending
                        _span_failed(
                            sink,
                            span=span,
                            error_message=safe_run_error_message(event.exception),
                            metadata={**metadata, "attempts": event.attempts},
                        )
                    else:
                        _fail_latest_step(
                            event.step_name,
                            spans=spans,
                            sink=sink,
                            error_message=safe_run_error_message(event.exception),
                            metadata={
                                "integration_id": "llamaindex-workflows",
                                "run_id": workflow_run_id,
                                "attempts": event.attempts,
                            },
                        )
                    _emit_projection(
                        sink,
                        context=context,
                        schema_id="llamaindex.step.v1",
                        owner_kind="execution_unit",
                        owner_external_id=f"{workflow_run_id}:{event.step_name}",
                        title=f"LlamaIndex step: {event.step_name}",
                        payload={
                            "run_id": workflow_run_id,
                            "step_name": event.step_name,
                            "status": "failed",
                            "attempts": event.attempts,
                            "error": safe_run_error_message(event.exception),
                        },
                        projection_kind="snapshot",
                        subject_kind="execution_unit",
                        subject_external_id=event.step_name,
                        sequence=10_000 + len(event_types),
                    )

            result = await cast(Awaitable[object], handler)
            for step_name, span, metadata in pending_terminals:
                completed_steps.append(step_name)
                _span_completed(sink, span=span, metadata=metadata)
        except Exception as exc:
            safe_message = safe_run_error_message(exc)
            for step_name, step_spans in tuple(spans.items()):
                while step_spans:
                    _span_failed(
                        sink,
                        span=step_spans.pop(),
                        error_message=safe_message,
                        metadata={
                            "integration_id": "llamaindex-workflows",
                            "run_id": workflow_run_id,
                            "step_name": step_name,
                        },
                    )
            raise

        output = dict(result) if isinstance(result, Mapping) else {"result": result}
        return WorkflowExecutionResult(
            output=output,
            metadata={
                "integration_id": "llamaindex-workflows",
                "workflow_kind": self.workflow_kind,
                "workflow_name": self.workflow.workflow_name,
                "workflow_run_id": workflow_run_id,
                "completed_steps": completed_steps,
                "failed_steps": failed_steps,
                "event_types": event_types,
                "last_step_name": completed_steps[-1] if completed_steps else "",
            },
        )


@dataclass(frozen=True, slots=True)
class LlamaIndexWorkflowsIntegrationProvider(WorkflowIntegrationProvider):
    definition: IntegrationDefinition = LLAMAINDEX_WORKFLOWS_INTEGRATION

    def wrap(self, target: object, *, context: IntegrationContext) -> object:
        if not callable(getattr(target, "run", None)):
            raise TypeError("LlamaIndex Workflows target must expose run()")
        if not isinstance(getattr(target, "workflow_name", None), str):
            raise TypeError(
                "LlamaIndex Workflows target must expose a string workflow_name"
            )
        run_kwargs = context.config.get("run_kwargs", {})
        if not isinstance(run_kwargs, Mapping):
            raise TypeError("LlamaIndex Workflows run_kwargs must be a mapping")
        return LlamaIndexWorkflowsExecutable(
            workflow=cast(_WorkflowCapable, target),
            workflow_kind=context.workflow_kind,
            run_kwargs=dict(run_kwargs),
        )


LLAMAINDEX_WORKFLOWS_PROVIDER = LlamaIndexWorkflowsIntegrationProvider()


def _worker_sequence(worker_id: object) -> int:
    try:
        return max(0, int(str(worker_id)))
    except (TypeError, ValueError):
        return 0


def _handle_step_state(
    event: StepStateChanged,
    *,
    sink: EventSink | None,
    context: WorkflowExecutionContext,
    workflow_run_id: str,
    spans: dict[str, list[SpanRef]],
    pending_terminals: list[tuple[str, SpanRef | None, dict[str, object]]],
) -> None:
    step_name = event.name
    external_id = f"{workflow_run_id}:{step_name}:{event.worker_id}"
    status = event.step_state.value
    if event.step_state is StepState.RUNNING:
        span = _span_started(
            sink,
            context=context,
            step_name=step_name,
            metadata={
                "integration_id": "llamaindex-workflows",
                "run_id": workflow_run_id,
                "worker_id": event.worker_id,
                "input_event": event.input_event_name,
            },
        )
        if span is not None:
            spans.setdefault(step_name, []).append(span)
    elif event.step_state is StepState.NOT_RUNNING:
        step_spans = spans.get(step_name, [])
        span = step_spans.pop() if step_spans else None
        pending_terminals.append(
            (
                step_name,
                span,
                {
                    "integration_id": "llamaindex-workflows",
                    "run_id": workflow_run_id,
                    "worker_id": event.worker_id,
                    "input_event": event.input_event_name,
                    "output_event": event.output_event_name or "",
                    "step_name": step_name,
                },
            )
        )
    projection_span: SpanRef | None = None
    if event.step_state is StepState.RUNNING:
        step_spans = spans.get(step_name, [])
        projection_span = step_spans[-1] if step_spans else None
    elif event.step_state is StepState.NOT_RUNNING:
        projection_span = span
    _emit_projection(
        sink,
        context=context,
        schema_id="llamaindex.step.v1",
        owner_kind="execution_unit",
        owner_external_id=external_id,
        title=f"LlamaIndex step: {step_name}",
        span=projection_span,
        payload={
            "run_id": workflow_run_id,
            "step_name": step_name,
            "worker_id": event.worker_id,
            "status": "running" if event.step_state is StepState.RUNNING else "succeeded",
            "runtime_state": status,
            "input_event": event.input_event_name,
            "output_event": event.output_event_name or "",
        },
        projection_kind="snapshot",
        subject_kind="execution_unit",
        subject_external_id=step_name,
        sequence=_worker_sequence(event.worker_id) * 10 + (0 if event.step_state is StepState.RUNNING else 1),
    )


def _span_started(
    sink: EventSink | None,
    *,
    context: WorkflowExecutionContext,
    step_name: str,
    metadata: Mapping[str, object],
) -> SpanRef | None:
    if sink is None or not isinstance(context.run_id, int):
        return None
    try:
        return sink.span_started(
            context.run_id,
            span_type="step",
            name=step_name,
            node_name=step_name,
            parent=cast(SpanRef | None, context.parent_span),
            metadata=metadata,
        )
    except Exception:
        return None


def _span_completed(
    sink: EventSink | None,
    *,
    span: SpanRef | None,
    metadata: Mapping[str, object],
) -> None:
    if sink is None or span is None:
        return
    suppress_observability_failure(
        lambda: sink.span_completed(
            span,
            output_summary=json.dumps(
                {"output_event": metadata.get("output_event", "")},
                ensure_ascii=False,
                sort_keys=True,
            ),
            metrics={"ok": True},
            metadata=metadata,
        ),
        context={"component": "llamaindex_integration", "operation": "step_completed"},
    )


def _span_failed(
    sink: EventSink | None,
    *,
    span: SpanRef | None,
    error_message: str,
    metadata: Mapping[str, object],
) -> None:
    if sink is None or span is None:
        return
    suppress_observability_failure(
        lambda: sink.span_failed(
            span,
            error_message=error_message,
            metrics={"ok": False},
            metadata=metadata,
        ),
        context={"component": "llamaindex_integration", "operation": "step_failed"},
    )


def _pop_pending_terminal(
    step_name: str,
    pending: list[tuple[str, SpanRef | None, dict[str, object]]],
) -> tuple[str, SpanRef | None, dict[str, object]] | None:
    for index in range(len(pending) - 1, -1, -1):
        if pending[index][0] == step_name:
            return pending.pop(index)
    return None


def _fail_latest_step(
    step_name: str,
    *,
    spans: dict[str, list[SpanRef]],
    sink: EventSink | None,
    error_message: str,
    metadata: Mapping[str, object],
) -> None:
    step_spans = spans.get(step_name, [])
    span = step_spans.pop() if step_spans else None
    _span_failed(sink, span=span, error_message=error_message, metadata=metadata)


def _event_summary(event: Event) -> object:
    try:
        dumped = event.model_dump(mode="json")
    except Exception:
        dumped = {"type": type(event).__name__}
    return summarize_mapping(dumped) if isinstance(dumped, Mapping) else dumped


def _emit_projection(
    sink: EventSink | None,
    *,
    context: WorkflowExecutionContext,
    schema_id: str,
    owner_kind: str,
    owner_external_id: str,
    title: str,
    payload: Mapping[str, object],
    span: SpanRef | None = None,
    projection_kind: str = "event",
    subject_kind: str = "run",
    subject_external_id: str = "",
    sequence: int = 0,
) -> None:
    callback = getattr(sink, "integration_projection", None)
    if not callable(callback) or not isinstance(context.run_id, int):
        return
    suppress_observability_failure(
        lambda: callback(
            context.run_id,
            integration_id="llamaindex-workflows",
            schema_id=schema_id,
            owner_kind=owner_kind,
            owner_external_id=owner_external_id,
            title=title,
            payload=payload,
            span=span,
            retention_class="execution_detail",
            classification="internal",
            projection_kind=projection_kind,
            subject_kind=subject_kind,
            subject_external_id=subject_external_id,
            sequence=sequence,
        ),
        context={
            "component": "llamaindex_integration",
            "operation": "integration_projection",
            "schema_id": schema_id,
        },
    )


def _run_awaitable(awaitable: Coroutine[Any, Any, T]) -> T:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(awaitable)

    future: Future[T] = Future()

    def runner() -> None:
        try:
            future.set_result(asyncio.run(awaitable))
        except BaseException as exc:
            future.set_exception(exc)

    thread = Thread(target=runner, daemon=True)
    thread.start()
    thread.join()
    return future.result()


__all__ = [
    "LLAMAINDEX_WORKFLOWS_PROVIDER",
    "LlamaIndexWorkflowsExecutable",
    "LlamaIndexWorkflowsIntegrationProvider",
]
