'''Run orchestration services.'''

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from django.db import transaction
from django.utils import timezone

from langgraph_automation.api.engine import EnginePreparedWorkflow
from langgraph_automation.api.errors import FrameworkError
from langgraph_automation.api.workflow import WorkflowResumeRequest
from langgraph_automation.apps.automation.models.run import Run, RunStatus
from langgraph_automation.apps.automation.policies.runs import (
    PolicyResult,
    can_cancel_run,
    can_resume_run,
    can_retry_run,
    can_start_run,
)
from langgraph_automation.apps.automation.services import runtime as runtime_module
from langgraph_automation.apps.automation.services.errors import WorkflowConfigurationError
from langgraph_automation.apps.automation.services.execution import (
    dispatch_prepared_workflow_execution,
    dispatch_prepared_workflow_resume,
)
from langgraph_automation.apps.automation.services.execution_result import ControlPlaneExecutionResult
from langgraph_automation.apps.automation.services.workflow_reference import parse_workflow_reference
from langgraph_automation.core.result_safety import safe_run_error_message, safe_run_output_payload
from langgraph_automation.integrations.observability.failure_policy import suppress_observability_failure


@dataclass(slots=True)
class RunActionResult:
    run: Run
    message: str = ''
    output_payload: dict[str, object] = field(default_factory=dict)
    execution_result: ControlPlaneExecutionResult | None = None


def _locked_run(run: Run) -> Run:
    return Run.objects.select_for_update().select_related('workflow').get(pk=run.pk)


def _policy_or_raise(policy: PolicyResult) -> None:
    if not policy.allowed:
        raise PermissionError(policy.reason)


def _transition_run(
    run: Run,
    *,
    status: str,
    thread_id: str | None = None,
    output_payload: dict[str, object] | None = None,
    message: str = '',
) -> Run:
    now = timezone.now()
    updates: list[str] = ['status', 'updated_at']
    run.status = status
    if thread_id is not None and thread_id != run.thread_id:
        run.thread_id = thread_id
        updates.append('thread_id')
    if output_payload is not None:
        run.output_payload = output_payload
        updates.append('output_payload')
    if status == RunStatus.RUNNING and run.started_at is None:
        run.started_at = now
        updates.append('started_at')
    if status in {RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.CANCELLED}:
        run.finished_at = now
        updates.append('finished_at')
    if message:
        run.error_message = message
        updates.append('error_message')
    run.save(update_fields=updates)
    return run


def _finalize_from_execution(run: Run, execution_result: ControlPlaneExecutionResult) -> Run:
    status = execution_result.status or RunStatus.FAILED
    message = safe_run_error_message(execution_result.error_message) if status == RunStatus.FAILED else ''
    return _transition_run(
        run,
        status=status,
        output_payload=safe_run_output_payload(execution_result.output_payload),
        message=message,
    )


def _emit_run_failed(*, event_sink, run: Run, error_message: str) -> None:
    if event_sink is None:
        return
    suppress_observability_failure(
        lambda: event_sink.run_failed(
            run.pk,
            error_message=error_message,
            payload={'run_id': run.pk, 'workflow_id': run.workflow_id},
        ),
        context={
            'component': 'runs',
            'operation': 'run_failed',
            'run_id': run.pk,
            'workflow_id': run.workflow_id,
        },
    )


def _handle_runtime_build_failure(run: Run, exc: Exception) -> RunActionResult:
    safe_message = safe_run_error_message(exc)
    with transaction.atomic():
        locked_run = _locked_run(run)
        _transition_run(locked_run, status=RunStatus.FAILED, message=safe_message)

    try:
        event_sink = runtime_module.build_event_sink(locked_run)
    except Exception:
        event_sink = None
    _emit_run_failed(event_sink=event_sink, run=locked_run, error_message=safe_message)

    return RunActionResult(
        run=locked_run,
        message='runtime configuration failed',
        output_payload={},
        execution_result=ControlPlaneExecutionResult(
            status=RunStatus.FAILED,
            error_message=str(exc),
            message='runtime configuration failed',
            details={'reason': 'workflow_configuration_error'},
        ),
    )


def _prepare_workflow_for_run(
    run: Run,
    *,
    services: runtime_module.RunExecutionServices | None,
) -> EnginePreparedWorkflow:
    reference = parse_workflow_reference(run.workflow.definition_payload)
    if reference is None:
        raise WorkflowConfigurationError("workflow reference is required.")
    return (services or runtime_module.get_run_execution_services()).prepare_workflow(reference)


def _event_sink(run: Run):
    try:
        return runtime_module.build_event_sink(run)
    except Exception:
        return None


def _complete_action(run: Run, execution_result: ControlPlaneExecutionResult) -> RunActionResult:
    with transaction.atomic():
        locked_run = _locked_run(run)
        _finalize_from_execution(locked_run, execution_result)
    return RunActionResult(
        run=locked_run,
        message=execution_result.message,
        output_payload=safe_run_output_payload(execution_result.output_payload),
        execution_result=execution_result,
    )


def start_run(
    *,
    run: Run,
    services: runtime_module.RunExecutionServices | None = None,
    actor: object | None = None,
) -> RunActionResult:
    with transaction.atomic():
        locked_run = _locked_run(run)
        _policy_or_raise(can_start_run(actor, locked_run))
        _transition_run(
            locked_run,
            status=RunStatus.RUNNING,
            thread_id=locked_run.thread_id or f'run-{locked_run.pk}',
        )
    try:
        prepared = _prepare_workflow_for_run(locked_run, services=services)
    except (WorkflowConfigurationError, FrameworkError) as exc:
        return _handle_runtime_build_failure(locked_run, exc)
    return _complete_action(
        locked_run,
        dispatch_prepared_workflow_execution(
            locked_run,
            prepared_workflow=prepared,
            event_sink=_event_sink(locked_run),
        ),
    )


def cancel_run(
    *,
    run: Run,
    services: runtime_module.RunExecutionServices | None = None,
    actor: object | None = None,
) -> RunActionResult:
    del services
    with transaction.atomic():
        locked_run = _locked_run(run)
        _policy_or_raise(can_cancel_run(actor, locked_run))
        _transition_run(locked_run, status=RunStatus.CANCELLED)
    sink = _event_sink(locked_run)
    if sink is not None:
        sink.run_cancelled(
            locked_run.pk,
            message='run cancelled',
            payload={'run_id': locked_run.pk, 'workflow_id': locked_run.workflow_id},
        )
    return RunActionResult(run=locked_run, message='run cancelled')


def resume_run(
    *,
    run: Run,
    resume_payload: Mapping[str, object],
    checkpoint_id: str | None = None,
    services: runtime_module.RunExecutionServices | None = None,
    actor: object | None = None,
) -> RunActionResult:
    with transaction.atomic():
        locked_run = _locked_run(run)
        _policy_or_raise(can_resume_run(actor, locked_run))
        _transition_run(locked_run, status=RunStatus.RUNNING)
    try:
        prepared = _prepare_workflow_for_run(locked_run, services=services)
    except (WorkflowConfigurationError, FrameworkError) as exc:
        return _handle_runtime_build_failure(locked_run, exc)
    request = WorkflowResumeRequest(value=resume_payload, checkpoint_id=checkpoint_id)
    return _complete_action(
        locked_run,
        dispatch_prepared_workflow_resume(
            locked_run,
            prepared_workflow=prepared,
            request=request,
            event_sink=_event_sink(locked_run),
        ),
    )


def retry_run(
    *,
    run: Run,
    services: runtime_module.RunExecutionServices | None = None,
    actor: object | None = None,
) -> RunActionResult:
    with transaction.atomic():
        locked_run = _locked_run(run)
        _policy_or_raise(can_retry_run(actor, locked_run))
        _transition_run(locked_run, status=RunStatus.RUNNING)
    try:
        prepared = _prepare_workflow_for_run(locked_run, services=services)
    except (WorkflowConfigurationError, FrameworkError) as exc:
        return _handle_runtime_build_failure(locked_run, exc)
    return _complete_action(
        locked_run,
        dispatch_prepared_workflow_execution(
            locked_run,
            prepared_workflow=prepared,
            event_sink=_event_sink(locked_run),
        ),
    )
