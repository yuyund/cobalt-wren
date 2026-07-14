'''Execution span model for graph, LLM, tool, checkpoint, and artifact steps.'''

from __future__ import annotations

from django.db import models


class ExecutionSpanType(models.TextChoices):
    '''Span categories used by observability and the UI.'''

    GRAPH = 'graph', 'Graph'
    NODE = 'node', 'Node'
    LLM = 'llm', 'LLM'
    TOOL = 'tool', 'Tool'
    CHECKPOINT = 'checkpoint', 'Checkpoint'
    ARTIFACT = 'artifact', 'Artifact'


class ExecutionSpanStatus(models.TextChoices):
    '''Span lifecycle states.'''

    PENDING = 'pending', 'Pending'
    RUNNING = 'running', 'Running'
    SUCCEEDED = 'succeeded', 'Succeeded'
    FAILED = 'failed', 'Failed'
    CANCELLED = 'cancelled', 'Cancelled'
    SKIPPED = 'skipped', 'Skipped'


class ExecutionSpan(models.Model):
    '''Common trace node for execution steps.'''

    run = models.ForeignKey('automation.Run', on_delete=models.CASCADE, related_name='spans')
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
    )
    span_type = models.CharField(max_length=32, choices=ExecutionSpanType.choices)
    name = models.CharField(max_length=200)
    status = models.CharField(max_length=32, choices=ExecutionSpanStatus.choices, default=ExecutionSpanStatus.PENDING)
    node_name = models.CharField(max_length=200, blank=True, default='')
    attempt = models.PositiveIntegerField(default=1)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    input_summary = models.TextField(blank=True, default='')
    output_summary = models.TextField(blank=True, default='')
    error_message = models.TextField(blank=True, default='')
    metrics = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    external_trace_id = models.CharField(max_length=255, blank=True, default='')
    external_span_id = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['run', 'span_type']),
            models.Index(fields=['run', 'node_name']),
        ]

    def __str__(self) -> str:
        return f'Span({self.pk}, {self.span_type}, {self.name}, {self.status})'

    @property
    def is_terminal_state(self) -> bool:
        return self.status in {
            ExecutionSpanStatus.SUCCEEDED,
            ExecutionSpanStatus.FAILED,
            ExecutionSpanStatus.CANCELLED,
            ExecutionSpanStatus.SKIPPED,
        }
