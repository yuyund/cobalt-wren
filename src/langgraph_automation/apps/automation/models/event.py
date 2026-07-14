'''Run event model for the Django control plane.'''

from __future__ import annotations

from django.db import models


class RunEventLevel(models.TextChoices):
    '''Log-like severity for append-only timeline entries.'''

    DEBUG = 'debug', 'Debug'
    INFO = 'info', 'Info'
    WARNING = 'warning', 'Warning'
    ERROR = 'error', 'Error'


class RunEvent(models.Model):
    '''Append-only event timeline for runs and spans.'''

    run = models.ForeignKey('automation.Run', on_delete=models.CASCADE, related_name='events')
    span = models.ForeignKey(
        'automation.ExecutionSpan',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='events',
    )
    event_type = models.CharField(max_length=100)
    level = models.CharField(max_length=16, choices=RunEventLevel.choices, default=RunEventLevel.INFO)
    node_name = models.CharField(max_length=200, blank=True, default='')
    message = models.TextField(blank=True, default='')
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['run', 'event_type']),
            models.Index(fields=['run', 'level']),
        ]

    def __str__(self) -> str:
        return f'Event({self.pk}, {self.event_type})'
