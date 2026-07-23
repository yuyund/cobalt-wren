'''Run policy helpers.'''

from __future__ import annotations

from dataclasses import dataclass

from langgraph_automation.apps.automation.models.run import Run, RunStatus


@dataclass(slots=True, frozen=True)
class PolicyResult:
    '''Simple allow/deny result shared by UI and services.'''

    allowed: bool
    reason: str = ''


def _result(condition: bool, reason: str) -> PolicyResult:
    return PolicyResult(allowed=condition, reason='' if condition else reason)


def can_start_run(actor: object | None, run: Run) -> PolicyResult:
    return _result(run.status == RunStatus.PENDING, f'Run is not pending: {run.status}')


def can_cancel_run(actor: object | None, run: Run) -> PolicyResult:
    return _result(run.status in {RunStatus.PENDING, RunStatus.RUNNING, RunStatus.WAITING}, f'Run cannot be cancelled from {run.status}')


def can_resume_run(actor: object | None, run: Run) -> PolicyResult:
    return _result(run.status == RunStatus.WAITING, f'Run cannot be resumed from {run.status}')


def can_retry_run(actor: object | None, run: Run) -> PolicyResult:
    return _result(run.status in {RunStatus.FAILED, RunStatus.CANCELLED}, f'Run cannot be retried from {run.status}')
