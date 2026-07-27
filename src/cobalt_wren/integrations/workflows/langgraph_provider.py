"""Official LangGraph workflow integration provider.

The provider uses LangGraph's public stream and Command APIs. It does not inspect
compiled graph private attributes or persist LangGraph runtime objects.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
import json
from typing import Any, Protocol, cast

from langgraph.types import Command

from cobalt_wren.api.integrations import (
    IntegrationContext,
    IntegrationDefinition,
    WorkflowIntegrationProvider,
)
from cobalt_wren.api.workflow import (
    WorkflowExecutionContext,
    WorkflowExecutionResult,
    WorkflowResumeRequest,
)
from cobalt_wren.core.result_safety import safe_run_error_message
from cobalt_wren.core.summary import summarize_mapping
from cobalt_wren.integrations.observability.base import EventSink
from cobalt_wren.integrations.observability.failure_policy import (
    suppress_observability_failure,
)
from cobalt_wren.integrations.observability.types import SpanRef
from cobalt_wren.integrations.workflows.definitions import (
    LANGGRAPH_INTEGRATION,
)


class _StreamCapable(Protocol):
    def stream(
        self,
        input: object,
        config: Mapping[str, object] | None = None,
        *,
        stream_mode: object = None,
    ) -> object: ...


@dataclass(slots=True)
class LangGraphExecutable:
    graph: _StreamCapable
    workflow_kind: str
    output_key: str | None = None
    invoke_config: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.invoke_config = dict(self.invoke_config)

    def execute(
        self,
        input_payload: Mapping[str, object],
        *,
        context: WorkflowExecutionContext,
    ) -> WorkflowExecutionResult:
        return self._run(dict(input_payload), context=context, resumed=False)

    def resume(
        self,
        request: WorkflowResumeRequest,
        *,
        context: WorkflowExecutionContext,
    ) -> WorkflowExecutionResult:
        return self._run(
            Command(resume=dict(request.value)),
            context=context,
            resumed=True,
        )

    def _run(
        self,
        graph_input: object,
        *,
        context: WorkflowExecutionContext,
        resumed: bool,
    ) -> WorkflowExecutionResult:
        config = _execution_config(self.invoke_config, context)
        sink = cast(EventSink | None, context.event_sink)
        spans: dict[str, SpanRef] = {}
        final_state: Mapping[str, object] = {}
        interrupts: list[object] = []
        completed_nodes: list[str] = []
        failed_nodes: list[str] = []
        latest_checkpoint_id = ""

        stream = self.graph.stream(
            graph_input,
            config,
            stream_mode=["debug", "values"],
        )
        try:
            for item in cast(Any, stream):
                if context.control is not None:
                    context.control.check()
                mode, value = _stream_part(item)
                if mode == "values" and isinstance(value, Mapping):
                    final_state = dict(value)
                    continue
                if mode != "debug" or not isinstance(value, Mapping):
                    continue
                event_type = str(value.get("type", ""))
                payload = value.get("payload")
                if not isinstance(payload, Mapping):
                    continue
                if event_type == "checkpoint":
                    latest_checkpoint_id = _checkpoint_id(payload) or latest_checkpoint_id
                    _emit_projection(
                        sink,
                        context=context,
                        schema_id="langgraph.checkpoint_ref.v1",
                        owner_kind="run",
                        owner_external_id=_checkpoint_id(payload),
                        title="LangGraph checkpoint",
                        payload={
                            "step": value.get("step"),
                            "checkpoint": _checkpoint_reference(payload),
                            "next_nodes": list(payload.get("next", ())),
                            "task_count": len(payload.get("tasks", ())),
                            "source": _metadata_value(payload, "source"),
                        },
                        retention_class="execution_detail",
                        projection_kind="reference",
                        subject_kind="checkpoint",
                        subject_external_id=_checkpoint_id(payload),
                        sequence=int(value.get("step") or 0),
                    )
                    continue
                if event_type == "task":
                    task_id = str(payload.get("id", ""))
                    node_name = str(payload.get("name", ""))
                    if task_id and node_name:
                        span = _node_started(
                            sink,
                            context=context,
                            node_name=node_name,
                            metadata={
                                "integration_id": "langgraph",
                                "task_id": task_id,
                                "step": value.get("step"),
                                "triggers": tuple(payload.get("triggers", ())),
                                "input_summary": _mapping_summary(payload.get("input")),
                            },
                        )
                        if span is not None:
                            spans[task_id] = span
                        _emit_projection(
                            sink,
                            context=context,
                            schema_id="langgraph.task.v1",
                            owner_kind="execution_unit",
                            owner_external_id=task_id,
                            title=f"LangGraph node: {node_name}",
                            span=span,
                            payload={
                                "task_id": task_id,
                                "node_name": node_name,
                                "status": "running",
                                "step": value.get("step"),
                                "triggers": list(payload.get("triggers", ())),
                            },
                            projection_kind="snapshot",
                            subject_kind="execution_unit",
                            subject_external_id=node_name,
                            sequence=int(value.get("step") or 0) * 10,
                        )
                    continue
                if event_type != "task_result":
                    continue
                task_id = str(payload.get("id", ""))
                node_name = str(payload.get("name", ""))
                error = payload.get("error")
                task_interrupts = payload.get("interrupts")
                if isinstance(task_interrupts, (list, tuple)):
                    interrupts.extend(task_interrupts)
                span = spans.pop(task_id, None)
                if error:
                    failed_nodes.append(node_name)
                    _node_failed(
                        sink,
                        span=span,
                        error_message=safe_run_error_message(error),
                        metadata={"integration_id": "langgraph", "task_id": task_id},
                    )
                else:
                    completed_nodes.append(node_name)
                    _node_completed(
                        sink,
                        span=span,
                        result=payload.get("result"),
                        metadata={
                            "integration_id": "langgraph",
                            "task_id": task_id,
                            "interrupt_count": len(task_interrupts or ()),
                        },
                    )
                _emit_projection(
                    sink,
                    context=context,
                    schema_id="langgraph.task.v1",
                    owner_kind="execution_unit",
                    owner_external_id=task_id,
                    title=f"LangGraph node: {node_name}",
                    span=span,
                    payload={
                        "task_id": task_id,
                        "node_name": node_name,
                        "status": "failed" if error else ("waiting" if task_interrupts else "succeeded"),
                        "error": safe_run_error_message(error) if error else "",
                        "interrupt_count": len(task_interrupts or ()),
                        "result_summary": _mapping_summary(payload.get("result")),
                    },
                    projection_kind="snapshot",
                    subject_kind="execution_unit",
                    subject_external_id=node_name,
                    sequence=int(value.get("step") or 0) * 10 + 1,
                )
                for task_interrupt in task_interrupts or ():
                    _emit_projection(
                        sink,
                        context=context,
                        schema_id="langgraph.interrupt.v1",
                        owner_kind="interaction",
                        owner_external_id=_interrupt_id(task_interrupt) or task_id,
                        title="LangGraph interrupt",
                        span=span,
                        payload={
                            "task_id": task_id,
                            "node_name": node_name,
                            "interrupt_id": _interrupt_id(task_interrupt),
                            "value": _safe_interrupt(task_interrupt),
                        },
                        projection_kind="snapshot",
                        subject_kind="interaction",
                        subject_external_id=_interrupt_id(task_interrupt) or task_id,
                        sequence=int(value.get("step") or 0) * 10 + 2,
                    )
        except Exception as exc:
            safe_message = safe_run_error_message(exc)
            for task_id, span in tuple(spans.items()):
                _node_failed(
                    sink,
                    span=span,
                    error_message=safe_message,
                    metadata={"integration_id": "langgraph", "task_id": task_id},
                )
            raise

        paused = bool(interrupts) or bool(final_state.get("__interrupt__"))
        if not interrupts and final_state.get("__interrupt__"):
            raw = final_state.get("__interrupt__")
            if isinstance(raw, (list, tuple)):
                interrupts.extend(raw)
            else:
                interrupts.append(raw)

        output = _select_output(final_state, self.output_key)
        if paused:
            _emit_projection(
                sink,
                context=context,
                schema_id="integration.actions.v1",
                owner_kind="interaction",
                owner_external_id=(
                    _interrupt_id(interrupts[0]) if interrupts else latest_checkpoint_id
                ),
                title="Available workflow actions",
                payload={
                    "actions": [
                        {
                            "action_id": "resume",
                            "target_kind": "run",
                            "label": "Resume",
                            "safety": "mutating",
                            "available": True,
                            "input_schema": {
                                "type": "object",
                                "properties": {
                                    "value": {
                                        "type": "string",
                                        "title": "Resume value",
                                        "format": "textarea",
                                        "description": "Value supplied to the waiting workflow.",
                                    }
                                },
                            },
                            "metadata": {
                                "checkpoint_id": latest_checkpoint_id,
                                "integration_id": "langgraph",
                            },
                        }
                    ]
                },
                retention_class="transient",
                projection_kind="action",
                subject_kind="action",
                subject_external_id="resume",
            )
            output = {
                **output,
                "interrupts": [_safe_interrupt(item) for item in interrupts],
                "allowed_actions": ["resume"],
            }
        return WorkflowExecutionResult(
            status="paused" if paused else "completed",
            output=output,
            metadata={
                "integration_id": "langgraph",
                "workflow_kind": self.workflow_kind,
                "resumed": resumed,
                "completed_nodes": completed_nodes,
                "failed_nodes": failed_nodes,
                "interrupt_count": len(interrupts),
                "last_step_name": completed_nodes[-1] if completed_nodes else "",
            },
        )


@dataclass(frozen=True, slots=True)
class LangGraphIntegrationProvider(WorkflowIntegrationProvider):
    definition: IntegrationDefinition = LANGGRAPH_INTEGRATION

    def wrap(self, target: object, *, context: IntegrationContext) -> object:
        stream = getattr(target, "stream", None)
        if not callable(stream):
            raise TypeError("LangGraph integration target must expose stream()")
        output_key = context.config.get("output_key")
        if output_key is not None and not isinstance(output_key, str):
            raise TypeError("LangGraph integration output_key must be a string")
        invoke_config = context.config.get("invoke_config", {})
        if not isinstance(invoke_config, Mapping):
            raise TypeError("LangGraph integration invoke_config must be a mapping")
        return LangGraphExecutable(
            graph=cast(_StreamCapable, target),
            workflow_kind=context.workflow_kind,
            output_key=output_key,
            invoke_config=dict(invoke_config),
        )


LANGGRAPH_PROVIDER = LangGraphIntegrationProvider()


def _execution_config(
    base: Mapping[str, object], context: WorkflowExecutionContext
) -> dict[str, object]:
    config = dict(base)
    configurable = config.get("configurable", {})
    if not isinstance(configurable, Mapping):
        configurable = {}
    config["configurable"] = {
        **dict(configurable),
        "thread_id": context.thread_id or str(context.run_id or "langgraph"),
    }
    return config


def _stream_part(item: object) -> tuple[str, object]:
    if isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], str):
        return item[0], item[1]
    return "debug", item


def _node_started(
    sink: EventSink | None,
    *,
    context: WorkflowExecutionContext,
    node_name: str,
    metadata: Mapping[str, object],
) -> SpanRef | None:
    if sink is None or not isinstance(context.run_id, int):
        return None
    try:
        return sink.span_started(
            context.run_id,
            span_type="node",
            name=node_name,
            node_name=node_name,
            parent=cast(SpanRef | None, context.parent_span),
            metadata=metadata,
        )
    except Exception:
        return None


def _node_completed(
    sink: EventSink | None,
    *,
    span: SpanRef | None,
    result: object,
    metadata: Mapping[str, object],
) -> None:
    if sink is None or span is None:
        return
    suppress_observability_failure(
        lambda: sink.span_completed(
            span,
            output_summary=_summary_text(result),
            metrics={"ok": True},
            metadata=metadata,
        ),
        context={"component": "langgraph_integration", "operation": "node_completed"},
    )


def _node_failed(
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
        context={"component": "langgraph_integration", "operation": "node_failed"},
    )


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
    retention_class: str = "execution_detail",
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
            integration_id="langgraph",
            schema_id=schema_id,
            owner_kind=owner_kind,
            owner_external_id=owner_external_id,
            title=title,
            payload=payload,
            span=span,
            retention_class=retention_class,
            classification="internal",
            projection_kind=projection_kind,
            subject_kind=subject_kind,
            subject_external_id=subject_external_id,
            sequence=sequence,
        ),
        context={
            "component": "langgraph_integration",
            "operation": "integration_projection",
            "schema_id": schema_id,
        },
    )


def _checkpoint_reference(payload: Mapping[str, object]) -> dict[str, object]:
    config = payload.get("config")
    parent = payload.get("parent_config")
    return {
        "thread_id": _configurable_value(config, "thread_id"),
        "checkpoint_id": _configurable_value(config, "checkpoint_id"),
        "checkpoint_namespace": _configurable_value(config, "checkpoint_ns"),
        "parent_checkpoint_id": _configurable_value(parent, "checkpoint_id"),
    }


def _checkpoint_id(payload: Mapping[str, object]) -> str:
    return str(_checkpoint_reference(payload).get("checkpoint_id", ""))


def _configurable_value(config: object, key: str) -> object:
    if not isinstance(config, Mapping):
        return ""
    configurable = config.get("configurable")
    if not isinstance(configurable, Mapping):
        return ""
    return configurable.get(key, "")


def _metadata_value(payload: Mapping[str, object], key: str) -> object:
    metadata = payload.get("metadata")
    if not isinstance(metadata, Mapping):
        return ""
    return metadata.get(key, "")


def _interrupt_id(value: object) -> str:
    if isinstance(value, Mapping):
        return str(value.get("id", ""))
    return str(getattr(value, "id", ""))


def _mapping_summary(value: object) -> object:
    if isinstance(value, Mapping):
        return summarize_mapping(dict(value))
    return {"type": type(value).__name__}


def _summary_text(value: object) -> str:
    summary = _mapping_summary(value)
    return json.dumps(summary, ensure_ascii=False, sort_keys=True, default=str)


def _safe_interrupt(value: object) -> object:
    raw = getattr(value, "value", value)
    if isinstance(raw, Mapping):
        return summarize_mapping(dict(raw))
    if isinstance(raw, (str, int, float, bool)) or raw is None:
        return raw
    return {"type": type(raw).__name__}


def _select_output(
    final_state: Mapping[str, object], output_key: str | None
) -> dict[str, object]:
    state = {key: value for key, value in final_state.items() if key != "__interrupt__"}
    if output_key is None:
        return state
    selected = state.get(output_key)
    if isinstance(selected, Mapping):
        return dict(selected)
    return {output_key: selected}


__all__ = [
    "LANGGRAPH_PROVIDER",
    "LangGraphExecutable",
    "LangGraphIntegrationProvider",
]
