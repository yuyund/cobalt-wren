"""Execution adapters for public prepared workflows."""
from __future__ import annotations

from collections.abc import Callable

from langgraph_automation.api.engine import EnginePreparedWorkflow
from langgraph_automation.api.errors import ExecutionError, FrameworkError, WorkflowCancelledError, WorkflowTimeoutError
from langgraph_automation.api.workflow import (
    WorkflowExecutionContext,
    WorkflowExecutionResult,
    WorkflowResumeRequest,
)
from langgraph_automation.apps.automation.models.run import Run, RunStatus
from langgraph_automation.apps.automation.services.execution_result import ControlPlaneExecutionResult
from langgraph_automation.apps.automation.services.execution_control import begin_execution_control, finish_execution_control
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
    return _dispatch(
        run,
        prepared_workflow=prepared_workflow,
        event_sink=event_sink,
        operation="execute",
        invoke=lambda context: prepared_workflow.execute(run.input_payload, context=context),
    )


def dispatch_prepared_workflow_resume(
    run: Run,
    *,
    prepared_workflow: EnginePreparedWorkflow,
    request: WorkflowResumeRequest,
    event_sink: EventSink | None = None,
) -> ControlPlaneExecutionResult:
    return _dispatch(
        run,
        prepared_workflow=prepared_workflow,
        event_sink=event_sink,
        operation="resume",
        invoke=lambda context: prepared_workflow.resume(request, context=context),
    )


def _dispatch(
    run: Run,
    *,
    prepared_workflow: EnginePreparedWorkflow,
    event_sink: EventSink | None,
    operation: str,
    invoke: Callable[[WorkflowExecutionContext], WorkflowExecutionResult],
) -> ControlPlaneExecutionResult:
    control_plane_owns_lifecycle = prepared_workflow.lifecycle_events_owner == "control_plane"
    graph_span: SpanRef | None = None
    raw_timeout = prepared_workflow.extra.get("timeout_seconds")
    timeout_seconds = float(raw_timeout) if isinstance(raw_timeout, (int, float)) and not isinstance(raw_timeout, bool) and raw_timeout > 0 else None
    control = begin_execution_control(run.pk, timeout_seconds=timeout_seconds)
    try:
        if event_sink is not None and control_plane_owns_lifecycle:
            suppress_observability_failure(
                lambda: event_sink.run_started(
                    run.pk,
                    message="run started" if operation == "execute" else "run resume started",
                    payload={"execution_path": "public_executable", "operation": operation},
                ),
                context={"component": "execution", "operation": "run_started", "run_id": run.pk},
            )
            try:
                graph_span = event_sink.span_started(
                    run.pk,
                    span_type="graph",
                    name="public-executable" if operation == "execute" else "public-executable-resume",
                    node_name="workflow",
                    metadata={"workflow_kind": prepared_workflow.kind, "operation": operation},
                )
            except Exception:
                graph_span = None

        result = invoke(
            WorkflowExecutionContext(
                run_id=run.pk,
                thread_id=run.thread_id,
                event_sink=event_sink,
                parent_span=graph_span,
                control=control,
            )
        )
    except Exception as exc:
        normalized_error = (
            exc
            if isinstance(exc, FrameworkError)
            else ExecutionError(
                safe_run_error_message(exc),
                code="WORKFLOW_EXECUTION_FAILED",
                component="execution",
                retryable=False,
                metadata={"workflow_kind": prepared_workflow.kind},
            )
        )
        safe_message = normalized_error.safe_message
        cancelled = isinstance(normalized_error, WorkflowCancelledError)
        timed_out = isinstance(normalized_error, WorkflowTimeoutError)
        if event_sink is not None and control_plane_owns_lifecycle:
            if graph_span is not None:
                suppress_observability_failure(
                    lambda: event_sink.span_failed(
                        graph_span,
                        error_message=safe_message,
                        metadata={"execution_path": "public_executable", "operation": operation},
                    ),
                    context={"component": "execution", "operation": "span_failed", "run_id": run.pk},
                )
            if cancelled:
                suppress_observability_failure(
                    lambda: event_sink.run_cancelled(run.pk, message=safe_message, payload={"execution_path": "public_executable", "operation": operation}),
                    context={"component": "execution", "operation": "run_cancelled", "run_id": run.pk},
                )
            else:
                suppress_observability_failure(
                    lambda: event_sink.run_failed(
                        run.pk,
                        error_message=safe_message,
                        payload={"execution_path": "public_executable", "operation": operation},
                    ),
                    context={"component": "execution", "operation": "run_failed", "run_id": run.pk},
                )
        finish_execution_control(run.pk)
        return ControlPlaneExecutionResult(
            status=RunStatus.CANCELLED if cancelled else (RunStatus.TIMED_OUT if timed_out else RunStatus.FAILED),
            error_message=safe_message,
            message="run failed",
            details={
                "execution_path": "public_executable",
                "workflow_kind": prepared_workflow.kind,
                "framework_error": True,
                "error_category": normalized_error.category,
                "error_code": normalized_error.code,
                "error_retryable": normalized_error.retryable,
                "lifecycle_events_owner": prepared_workflow.lifecycle_events_owner,
                "engine_generation": prepared_workflow.engine_generation,
                "engine_signature": prepared_workflow.engine_signature,
                "operation": operation,
            },
        )

    finish_execution_control(run.pk)
    paused = result.status == "paused"
    if event_sink is not None and control_plane_owns_lifecycle:
        if graph_span is not None:
            suppress_observability_failure(
                lambda: event_sink.span_completed(
                    graph_span,
                    output_summary=str(dict(result.output)),
                    metrics={"ok": True, "paused": paused},
                    metadata={"execution_path": "public_executable", "operation": operation},
                ),
                context={"component": "execution", "operation": "span_completed", "run_id": run.pk},
            )
        if not paused:
            suppress_observability_failure(
                lambda: event_sink.run_completed(
                    run.pk,
                    message="run completed",
                    payload={"execution_path": "public_executable", "operation": operation},
                ),
                context={"component": "execution", "operation": "run_completed", "run_id": run.pk},
            )

    return ControlPlaneExecutionResult(
        status=RunStatus.WAITING if paused else RunStatus.SUCCEEDED,
        output_payload=result.output,
        message="run paused" if paused else "run completed",
        last_step_name=str(result.metadata.get("last_step_name", "")),
        details={
            "execution_path": "public_executable",
            "workflow_kind": prepared_workflow.kind,
            "workflow_metadata": result.metadata,
            "lifecycle_events_owner": prepared_workflow.lifecycle_events_owner,
            "engine_generation": prepared_workflow.engine_generation,
            "engine_signature": prepared_workflow.engine_signature,
            "operation": operation,
            "paused": paused,
        },
    )
