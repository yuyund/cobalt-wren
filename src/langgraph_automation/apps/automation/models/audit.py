"""Append-only control-plane operation audit records."""

from __future__ import annotations

from django.db import models

from langgraph_automation.core.summary import summarize_display_value


class OperationAuditLog(models.Model):
    actor_identifier = models.CharField(max_length=255, blank=True, default="")
    action = models.CharField(max_length=100)
    target_type = models.CharField(max_length=100)
    target_id = models.CharField(max_length=100)
    run = models.ForeignKey(
        "automation.Run",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
    )
    outcome = models.CharField(max_length=32)
    payload_summary = models.JSONField(default=dict, blank=True)
    message = models.CharField(max_length=500, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["target_type", "target_id"],
                name="auto_audit_target_idx",
            ),
            models.Index(
                fields=["action", "outcome"], name="automation_o_action_0e6831_idx"
            ),
        ]

    @property
    def safe_payload_summary(self) -> object:
        return summarize_display_value(self.payload_summary)
