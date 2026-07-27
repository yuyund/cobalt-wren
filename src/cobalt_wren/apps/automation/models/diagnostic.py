"""Bounded, redacted diagnostic payload snapshots for progressive inspection."""
from __future__ import annotations
from django.db import models
from django.utils import timezone

class DiagnosticPayload(models.Model):
    run = models.ForeignKey(
        "automation.Run", null=True, blank=True, on_delete=models.CASCADE, related_name="diagnostic_payloads"
    )
    target_type = models.CharField(max_length=32)
    target_id = models.PositiveBigIntegerField()
    field_name = models.CharField(max_length=100)
    payload = models.JSONField(default=dict, blank=True)
    byte_size = models.PositiveIntegerField(default=0)
    truncated = models.BooleanField(default=False)
    truncation_reason = models.CharField(max_length=64, blank=True, default="")
    expires_at = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["target_type", "target_id", "field_name"],
                name="unique_diagnostic_target_field",
            )
        ]
        indexes = [
            models.Index(fields=["target_type", "target_id"], name="auto_diag_target_idx"),
        ]

    @property
    def is_expired(self) -> bool:
        return self.expires_at <= timezone.now()
