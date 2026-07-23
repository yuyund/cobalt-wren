'''Run model for the Django control plane.'''

from __future__ import annotations

from django.db import models

from langgraph_automation.core.summary import summarize_display_value


class RunStatus(models.TextChoices):
    '''Lifecycle states for a workflow run.'''

    PENDING = 'pending', 'Pending'
    RUNNING = 'running', 'Running'
    WAITING = 'waiting', 'Waiting'
    SUCCEEDED = 'succeeded', 'Succeeded'
    FAILED = 'failed', 'Failed'
    TIMED_OUT = 'timed_out', 'Timed out'
    CANCELLED = 'cancelled', 'Cancelled'


class Run(models.Model):
    '''Persistent run metadata. Execution logic lives in graphs/, not here.'''

    workflow = models.ForeignKey('automation.Workflow', on_delete=models.CASCADE, related_name='runs')
    name = models.CharField(max_length=200)
    status = models.CharField(max_length=32, choices=RunStatus.choices, default=RunStatus.PENDING)
    thread_id = models.CharField(max_length=255, blank=True, default='', db_index=True)
    input_payload = models.JSONField(default=dict, blank=True)
    output_payload = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True, default='')
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    last_event_at = models.DateTimeField(null=True, blank=True)
    last_span_name = models.CharField(max_length=200, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        permissions = [("start_run", "Can start run"), ("resume_run", "Can resume run"), ("cancel_run", "Can cancel run"), ("retry_run", "Can retry run")]
        indexes = [
            models.Index(fields=['workflow', 'status']),
            models.Index(fields=['thread_id']),
        ]

    def __str__(self) -> str:
        return f'Run({self.pk}, {self.name}, {self.status})'

    @property
    def is_running_state(self) -> bool:
        return self.status == RunStatus.RUNNING

    @property
    def is_terminal_state(self) -> bool:
        return self.status in {RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.TIMED_OUT, RunStatus.CANCELLED}

    @property
    def input_payload_summary(self) -> object:
        return summarize_display_value(self.input_payload)

    @property
    def output_payload_summary(self) -> object:
        return summarize_display_value(self.output_payload)
