"""Inline or worker-mode Run operation dispatch."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from django.conf import settings

from cobalt_wren.apps.automation.models import ExecutionJob, ExecutionJobOperation, Run
from cobalt_wren.apps.automation.services.jobs import enqueue_execution_job
from cobalt_wren.apps.automation.services.runs import RunActionResult, cancel_run, resume_run, retry_run, start_run


@dataclass(frozen=True, slots=True)
class DispatchedRunAction:
    run: Run
    result: RunActionResult | None = None
    job: ExecutionJob | None = None


def worker_mode_enabled() -> bool:
    return str(getattr(settings, "COBALT_WREN_EXECUTION_MODE", "inline")).strip().lower() == "worker"


def dispatch_start(*, run: Run, actor: object | None = None) -> DispatchedRunAction:
    if worker_mode_enabled():
        return DispatchedRunAction(run=run, job=enqueue_execution_job(run=run, operation=ExecutionJobOperation.START))
    return DispatchedRunAction(run=run, result=start_run(run=run, actor=actor))


def dispatch_resume(*, run: Run, payload: Mapping[str, object], checkpoint_id: str | None = None, actor: object | None = None) -> DispatchedRunAction:
    if worker_mode_enabled():
        return DispatchedRunAction(run=run, job=enqueue_execution_job(run=run, operation=ExecutionJobOperation.RESUME, payload=payload, checkpoint_id=checkpoint_id))
    return DispatchedRunAction(run=run, result=resume_run(run=run, resume_payload=payload, checkpoint_id=checkpoint_id, actor=actor))


def dispatch_retry(*, run: Run, actor: object | None = None) -> DispatchedRunAction:
    if worker_mode_enabled():
        return DispatchedRunAction(run=run, job=enqueue_execution_job(run=run, operation=ExecutionJobOperation.RETRY))
    return DispatchedRunAction(run=run, result=retry_run(run=run, actor=actor))


def dispatch_cancel(*, run: Run, actor: object | None = None) -> DispatchedRunAction:
    return DispatchedRunAction(run=run, result=cancel_run(run=run, actor=actor))
