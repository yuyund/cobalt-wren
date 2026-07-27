'''Run policy helpers.'''

from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings

from cobalt_wren.apps.automation.models.run import Run, RunStatus


@dataclass(slots=True, frozen=True)
class PolicyResult:
    '''Simple allow/deny result shared by UI and services.'''

    allowed: bool
    reason: str = ''


def _result(condition: bool, reason: str) -> PolicyResult:
    return PolicyResult(allowed=condition, reason='' if condition else reason)


def _permission(actor: object | None, codename: str) -> PolicyResult:
    if actor is None or not bool(getattr(settings, "COBALT_WREN_REQUIRE_LOGIN", False)):
        return PolicyResult(True)
    has_perm = getattr(actor, "has_perm", None)
    allowed = bool(callable(has_perm) and has_perm(f"automation.{codename}"))
    return PolicyResult(allowed, "Actor does not have permission" if not allowed else "")


def _combine(permission: PolicyResult, state: PolicyResult) -> PolicyResult:
    return permission if not permission.allowed else state


def can_start_run(actor: object | None, run: Run) -> PolicyResult:
    return _combine(_permission(actor, 'start_run'), _result(run.status == RunStatus.PENDING, f'Run is not pending: {run.status}'))


def can_cancel_run(actor: object | None, run: Run) -> PolicyResult:
    return _combine(_permission(actor, 'cancel_run'), _result(run.status in {RunStatus.PENDING, RunStatus.RUNNING, RunStatus.WAITING}, f'Run cannot be cancelled from {run.status}'))


def can_resume_run(actor: object | None, run: Run) -> PolicyResult:
    return _combine(_permission(actor, 'resume_run'), _result(run.status == RunStatus.WAITING, f'Run cannot be resumed from {run.status}'))


def can_retry_run(actor: object | None, run: Run) -> PolicyResult:
    return _combine(_permission(actor, 'retry_run'), _result(run.status in {RunStatus.FAILED, RunStatus.TIMED_OUT, RunStatus.CANCELLED}, f'Run cannot be retried from {run.status}'))
