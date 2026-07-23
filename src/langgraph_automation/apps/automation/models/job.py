"""Database-backed execution job/outbox model."""

from __future__ import annotations

from django.db import models
from django.utils import timezone


class ExecutionJobStatus(models.TextChoices):
    QUEUED = "queued", "Queued"
    CLAIMED = "claimed", "Claimed"
    SUCCEEDED = "succeeded", "Succeeded"
    FAILED = "failed", "Failed"
    CANCELLED = "cancelled", "Cancelled"


class ExecutionJobOperation(models.TextChoices):
    START = "start", "Start"
    RESUME = "resume", "Resume"
    RETRY = "retry", "Retry"


class ExecutionJob(models.Model):
    run = models.ForeignKey(
        "automation.Run", on_delete=models.CASCADE, related_name="execution_jobs"
    )
    operation = models.CharField(max_length=16, choices=ExecutionJobOperation.choices)
    status = models.CharField(
        max_length=16,
        choices=ExecutionJobStatus.choices,
        default=ExecutionJobStatus.QUEUED,
    )
    payload = models.JSONField(default=dict, blank=True)
    checkpoint_id = models.CharField(max_length=255, blank=True, default="")
    worker_id = models.CharField(max_length=255, blank=True, default="")
    attempts = models.PositiveIntegerField(default=0)
    available_at = models.DateTimeField(default=timezone.now)
    claimed_at = models.DateTimeField(null=True, blank=True)
    heartbeat_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    error_message = models.CharField(max_length=500, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(
                fields=["status", "available_at"], name="automation_e_status_70f3cf_idx"
            ),
            models.Index(
                fields=["worker_id", "status"], name="auto_job_worker_status_idx"
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["run"],
                condition=models.Q(status__in=["queued", "claimed"]),
                name="one_active_execution_job_per_run",
            )
        ]
