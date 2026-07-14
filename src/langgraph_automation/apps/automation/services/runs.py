'''Run orchestration services.'''

from __future__ import annotations

from dataclasses import dataclass, field

from django.db import transaction
from django.utils import timezone

from langgraph_automation.apps.automation.models.run import Run, RunStatus
from langgraph_automation.apps.automation.policies.runs import PolicyResult, can_cancel_run, can_retry_run, can_start_run
from langgraph_automation.apps.automation.services import runtime as runtime_module
from langgraph_automation.apps.automation.services.errors import WorkflowConfigurationError
from langgraph_automation.apps.automation.services.execution import dispatch_run_execution
from langgraph_automation.core.result_safety import safe_run_error_message, safe_run_output_payload
from langgraph_automation.graphs.runner import ExecutionResult
from langgraph_automation.graphs.runtime import GraphRuntime
from langgraph_automation.integrations.observability.failure_policy import suppress_observability_failure


@dataclass(slots=True)
class RunActionResult:
    '''Result from a run lifecycle action.'''

    run: Run
    message: str = ''
    output_payload: dict[str, object] = field(default_factory=dict)
    execution_result: ExecutionResult | None = None


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


def _finalize_from_execution(run: Run, execution_result: ExecutionResult) -> Run:
    status = execution_result.status or RunStatus.FAILED
    message = safe_run_error_message(execution_result.error_message) if status == RunStatus.FAILED else ''
    return _transition_run(
        run,
        status=status,
        output_payload=safe_run_output_payload(execution_result.output_payload),
        message=message,
    )


def _make_runtime(run: Run, runtime: GraphRuntime | None) -> GraphRuntime:
    return runtime if runtime is not None else runtime_module.build_graph_runtime(run)


def _emit_run_failed(*, event_sink, run: Run, error_message: str) -> None:
    if event_sink is None:
        return
    suppress_observability_failure(
        lambda: event_sink.run_failed(
            run.pk,
            error_message=error_message,
            payload={'run_id': run.pk, 'workflow_id': run.workflow_id},
        ),
        context={'component': 'runs', 'operation': 'run_failed', 'run_id': run.pk, 'workflow_id': run.workflow_id},
    )


def _handle_runtime_build_failure(run: Run, exc: WorkflowConfigurationError) -> RunActionResult:
    safe_message = safe_run_error_message(exc)
    with transaction.atomic():
        locked_run = _locked_run(run)
        _transition_run(locked_run, status=RunStatus.FAILED, message=safe_message)

    try:
        event_sink = runtime_module.build_event_sink(locked_run)
    except Exception:  # pragma: no cover - observability failures are best-effort
        event_sink = None
    _emit_run_failed(event_sink=event_sink, run=locked_run, error_message=safe_message)

    return RunActionResult(
        run=locked_run,
        message='runtime configuration failed',
        output_payload={},
        execution_result=ExecutionResult(
            status=RunStatus.FAILED,
            error_message=str(exc),
            message='runtime configuration failed',
            details={'reason': 'workflow_configuration_error'},
        ),
    )


def start_run(*, run: Run, runtime: GraphRuntime | None = None, actor: object | None = None) -> RunActionResult:
    '''Start a run.'''

    with transaction.atomic():
        locked_run = _locked_run(run)
        _policy_or_raise(can_start_run(actor, locked_run))
        thread_id = locked_run.thread_id or f'run-{locked_run.pk}'
        _transition_run(locked_run, status=RunStatus.RUNNING, thread_id=thread_id)

    try:
        runtime = _make_runtime(locked_run, runtime)
    except WorkflowConfigurationError as exc:
        return _handle_runtime_build_failure(locked_run, exc)

    try:
        execution_result = dispatch_run_execution(locked_run, runtime=runtime)
    except Exception as exc:  # pragma: no cover
        with transaction.atomic():
            locked_run = _locked_run(locked_run)
            _transition_run(locked_run, status=RunStatus.FAILED, message=safe_run_error_message(exc))
        _emit_run_failed(event_sink=runtime.event_sink, run=locked_run, error_message=safe_run_error_message(exc))
        raise

    with transaction.atomic():
        locked_run = _locked_run(locked_run)
        _finalize_from_execution(locked_run, execution_result)
    return RunActionResult(run=locked_run, message=execution_result.message, output_payload=safe_run_output_payload(execution_result.output_payload), execution_result=execution_result)


def cancel_run(*, run: Run, runtime: GraphRuntime | None = None, actor: object | None = None) -> RunActionResult:
    '''Cancel a run.'''

    with transaction.atomic():
        locked_run = _locked_run(run)
        _policy_or_raise(can_cancel_run(actor, locked_run))
        _transition_run(locked_run, status=RunStatus.CANCELLED)

    runtime = _make_runtime(locked_run, runtime)
    if runtime.event_sink is not None:
        runtime.event_sink.run_cancelled(locked_run.pk, message='run cancelled', payload={'run_id': locked_run.pk, 'workflow_id': locked_run.workflow_id})
    return RunActionResult(run=locked_run, message='run cancelled')


def resume_run(*, run: Run, runtime: GraphRuntime | None = None, actor: object | None = None) -> RunActionResult:
    '''Resume a run from checkpoint.'''

    raise NotImplementedError('resume_run is not implemented until checkpoint resume semantics are defined; use retry_run instead')


def retry_run(*, run: Run, runtime: GraphRuntime | None = None, actor: object | None = None) -> RunActionResult:
    '''Retry a failed or cancelled run.'''

    with transaction.atomic():
        locked_run = _locked_run(run)
        _policy_or_raise(can_retry_run(actor, locked_run))
        _transition_run(locked_run, status=RunStatus.RUNNING)

    try:
        runtime = _make_runtime(locked_run, runtime)
    except WorkflowConfigurationError as exc:
        return _handle_runtime_build_failure(locked_run, exc)

    try:
        execution_result = dispatch_run_execution(locked_run, runtime=runtime)
    except Exception as exc:  # pragma: no cover
        with transaction.atomic():
            locked_run = _locked_run(locked_run)
            _transition_run(locked_run, status=RunStatus.FAILED, message=safe_run_error_message(exc))
        _emit_run_failed(event_sink=runtime.event_sink, run=locked_run, error_message=safe_run_error_message(exc))
        raise

    with transaction.atomic():
        locked_run = _locked_run(locked_run)
        _finalize_from_execution(locked_run, execution_result)
    return RunActionResult(run=locked_run, message=execution_result.message, output_payload=safe_run_output_payload(execution_result.output_payload), execution_result=execution_result)
