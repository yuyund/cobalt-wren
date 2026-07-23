"""Database-backed execution job enqueue, claim, heartbeat, and execution."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import timedelta
import socket

from django.db import transaction
from django.utils import timezone

from langgraph_automation.apps.automation.models import (
    ExecutionJob,
    ExecutionJobOperation,
    ExecutionJobStatus,
    Run,
)
from langgraph_automation.apps.automation.services.runs import (
    resume_run,
    retry_run,
    start_run,
)
from langgraph_automation.core.result_safety import safe_run_error_message


def enqueue_execution_job(
    *,
    run: Run,
    operation: str,
    payload: Mapping[str, object] | None = None,
    checkpoint_id: str | None = None,
) -> ExecutionJob:
    if operation not in ExecutionJobOperation.values:
        raise ValueError("unsupported execution job operation")
    return ExecutionJob.objects.create(
        run=run,
        operation=operation,
        payload=dict(payload or {}),
        checkpoint_id=checkpoint_id or "",
        available_at=timezone.now(),
    )


def claim_next_job(*, worker_id: str | None = None) -> ExecutionJob | None:
    identity = (worker_id or socket.gethostname())[:255]
    with transaction.atomic():
        job = (
            ExecutionJob.objects.select_for_update()
            .filter(status=ExecutionJobStatus.QUEUED, available_at__lte=timezone.now())
            .order_by("created_at")
            .first()
        )
        if job is None:
            return None
        now = timezone.now()
        job.status = ExecutionJobStatus.CLAIMED
        job.worker_id = identity
        job.claimed_at = now
        job.heartbeat_at = now
        job.attempts += 1
        job.save(
            update_fields=[
                "status",
                "worker_id",
                "claimed_at",
                "heartbeat_at",
                "attempts",
                "updated_at",
            ]
        )
        return job


def heartbeat_job(job: ExecutionJob) -> None:
    ExecutionJob.objects.filter(pk=job.pk, status=ExecutionJobStatus.CLAIMED).update(
        heartbeat_at=timezone.now()
    )


def recover_stale_jobs(*, stale_after_seconds: int = 300) -> int:
    cutoff = timezone.now() - timedelta(seconds=stale_after_seconds)
    return ExecutionJob.objects.filter(
        status=ExecutionJobStatus.CLAIMED, heartbeat_at__lt=cutoff
    ).update(
        status=ExecutionJobStatus.QUEUED,
        worker_id="",
        claimed_at=None,
        heartbeat_at=None,
        available_at=timezone.now(),
    )


def execute_job(job: ExecutionJob) -> ExecutionJob:
    try:
        run = Run.objects.select_related("workflow").get(pk=job.run_id)
        if job.operation == ExecutionJobOperation.START:
            start_run(run=run)
        elif job.operation == ExecutionJobOperation.RESUME:
            resume_run(
                run=run,
                resume_payload=job.payload,
                checkpoint_id=job.checkpoint_id or None,
            )
        else:
            retry_run(run=run)
        job.status = ExecutionJobStatus.SUCCEEDED
        job.error_message = ""
        job.finished_at = timezone.now()
        job.save(update_fields=["status", "error_message", "finished_at", "updated_at"])
        return job
    except Exception as exc:
        job.status = ExecutionJobStatus.FAILED
        job.error_message = safe_run_error_message(exc)[:500]
        job.finished_at = timezone.now()
        job.save(update_fields=["status", "error_message", "finished_at", "updated_at"])
        return job
