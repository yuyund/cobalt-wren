"""Execution adapters for legacy graphs and public prepared workflows."""
from __future__ import annotations

from langgraph_automation.api.engine import EnginePreparedWorkflow
from langgraph_automation.api.workflow import WorkflowExecutionContext
from langgraph_automation.api.errors import FrameworkError
from langgraph_automation.apps.automation.models.run import Run
from langgraph_automation.apps.automation.services.execution_result import ControlPlaneExecutionResult
from langgraph_automation.core.result_safety import safe_run_error_message
from langgraph_automation.integrations.observability.base import EventSink
from langgraph_automation.integrations.observability.failure_policy import suppress_observability_failure
from langgraph_automation.integrations.observability.types import SpanRef


def dispatch_prepared_workflow_execution(
    run: Run,
    *,
    prepared_workflow: EnginePreparedWorkflow,
    event_sink: EventSink | None = None,
) -> ControlPlaneExecutionResult:
    """Execute a public workflow and adapt it to the control-plane result."""
    control_plane_owns_lifecycle = prepared_workflow.lifecycle_events_owner == "control_plane"
    graph_span: SpanRef | None = None
    try:
        if event_sink is not None and control_plane_owns_lifecycle:
            suppress_observability_failure(
                lambda: event_sink.run_started(
                    run.pk,
                    message="run started",
                    payload={"execution_path": "public_executable"},
                ),
                context={"component": "execution", "operation": "run_started", "run_id": run.pk},
            )
            try:
                graph_span = event_sink.span_started(
                    run.pk,
                    span_type="graph",
                    name="public-executable",
                    node_name="workflow",
                    metadata={"workflow_kind": prepared_workflow.kind},
                )
            except Exception:
                graph_span = None

        result = prepared_workflow.execute(
            run.input_payload,
            context=WorkflowExecutionContext(
                run_id=run.pk,
                thread_id=run.thread_id,
                event_sink=event_sink,
                parent_span=graph_span,
            ),
        )
    except Exception as exc:
        safe_message = safe_run_error_message(exc)
        if event_sink is not None and control_plane_owns_lifecycle:
            if graph_span is not None:
                suppress_observability_failure(
                    lambda: event_sink.span_failed(
                        graph_span,
                        error_message=safe_message,
                        metadata={"execution_path": "public_executable"},
                    ),
                    context={"component": "execution", "operation": "span_failed", "run_id": run.pk},
                )
            suppress_observability_failure(
                lambda: event_sink.run_failed(
                    run.pk,
                    error_message=safe_message,
                    payload={"execution_path": "public_executable"},
                ),
                context={"component": "execution", "operation": "run_failed", "run_id": run.pk},
            )
        return ControlPlaneExecutionResult(
            status="failed",
            error_message=str(exc),
            message="run failed",
            details={
                "execution_path": "public_executable",
                "workflow_kind": prepared_workflow.kind,
                "framework_error": isinstance(exc, FrameworkError),
                "lifecycle_events_owner": prepared_workflow.lifecycle_events_owner,
                "engine_generation": prepared_workflow.engine_generation,
                "engine_signature": prepared_workflow.engine_signature,
            },
        )

    if event_sink is not None and control_plane_owns_lifecycle:
        if graph_span is not None:
            suppress_observability_failure(
                lambda: event_sink.span_completed(
                    graph_span,
                    output_summary=str(dict(result.output)),
                    metrics={"ok": True},
                    metadata={"execution_path": "public_executable"},
                ),
                context={"component": "execution", "operation": "span_completed", "run_id": run.pk},
            )
        suppress_observability_failure(
            lambda: event_sink.run_completed(
                run.pk,
                message="run completed",
                payload={"execution_path": "public_executable"},
            ),
            context={"component": "execution", "operation": "run_completed", "run_id": run.pk},
        )

    return ControlPlaneExecutionResult(
        status="succeeded",
        output_payload=result.output,
        message="run completed",
        last_step_name=str(result.metadata.get("last_step_name", "")),
        details={
            "execution_path": "public_executable",
            "workflow_kind": prepared_workflow.kind,
            "workflow_metadata": result.metadata,
            "lifecycle_events_owner": prepared_workflow.lifecycle_events_owner,
            "engine_generation": prepared_workflow.engine_generation,
            "engine_signature": prepared_workflow.engine_signature,
        },
    )
