"""Bounded integration-specific projections attached to canonical control-plane records."""

from __future__ import annotations

from django.db import models
from django.utils import timezone

from cobalt_wren.core.summary import summarize_display_value


class IntegrationProjectionOwnerKind(models.TextChoices):
    RUN = "run", "Run"
    EXECUTION_UNIT = "execution_unit", "Execution unit"
    INTERACTION = "interaction", "Interaction"
    ARTIFACT = "artifact", "Artifact"
    CHECKPOINT = "checkpoint", "Checkpoint"


class IntegrationProjectionKind(models.TextChoices):
    SNAPSHOT = "snapshot", "Snapshot"
    EVENT = "event", "Event"
    REFERENCE = "reference", "Reference"
    ACTION = "action", "Action"


class IntegrationProjectionSubjectKind(models.TextChoices):
    RUN = "run", "Run"
    EXECUTION_UNIT = "execution_unit", "Execution unit"
    INTERACTION = "interaction", "Interaction"
    ARTIFACT = "artifact", "Artifact"
    CHECKPOINT = "checkpoint", "Checkpoint"
    ACTION = "action", "Action"


class IntegrationProjectionRecord(models.Model):
    """Append-only, versioned OSS-specific detail retained by the control plane."""

    run = models.ForeignKey(
        "automation.Run",
        on_delete=models.CASCADE,
        related_name="integration_projections",
    )
    span = models.ForeignKey(
        "automation.ExecutionSpan",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="integration_projections",
    )
    integration_id = models.CharField(max_length=100, db_index=True)
    schema_id = models.CharField(max_length=200, db_index=True)
    owner_kind = models.CharField(
        max_length=32,
        choices=IntegrationProjectionOwnerKind.choices,
        default=IntegrationProjectionOwnerKind.RUN,
    )
    owner_external_id = models.CharField(max_length=255, blank=True, default="")
    projection_kind = models.CharField(
        max_length=32,
        choices=IntegrationProjectionKind.choices,
        default=IntegrationProjectionKind.EVENT,
        db_index=True,
    )
    subject_kind = models.CharField(
        max_length=32,
        choices=IntegrationProjectionSubjectKind.choices,
        default=IntegrationProjectionSubjectKind.RUN,
        db_index=True,
    )
    subject_external_id = models.CharField(max_length=255, blank=True, default="")
    sequence = models.PositiveBigIntegerField(default=0)
    occurred_at = models.DateTimeField(default=timezone.now, db_index=True)
    title = models.CharField(max_length=200, blank=True, default="")
    payload = models.JSONField(default=dict, blank=True)
    byte_size = models.PositiveIntegerField(default=0)
    truncated = models.BooleanField(default=False)
    truncation_reason = models.CharField(max_length=64, blank=True, default="")
    retention_class = models.CharField(max_length=64, default="execution_detail")
    classification = models.CharField(max_length=64, default="internal")
    expires_at = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["occurred_at", "sequence", "created_at"]
        indexes = [
            models.Index(fields=["run", "integration_id"], name="auto_proj_run_int_idx"),
            models.Index(fields=["span", "schema_id"], name="auto_proj_span_schema_idx"),
            models.Index(fields=["run", "owner_kind"], name="auto_proj_run_owner_idx"),
            models.Index(fields=["run", "projection_kind"], name="auto_proj_run_kind_idx"),
            models.Index(fields=["run", "subject_kind", "subject_external_id"], name="auto_proj_subject_idx"),
        ]

    @property
    def is_expired(self) -> bool:
        return self.expires_at <= timezone.now()

    @property
    def payload_summary(self) -> object:
        return summarize_display_value(self.payload)
