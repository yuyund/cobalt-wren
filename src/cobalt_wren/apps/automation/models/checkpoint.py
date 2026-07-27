'''Checkpoint metadata model for resume support and UI indexing.'''

from __future__ import annotations

from django.db import models


class CheckpointMetadata(models.Model):
    '''Checkpoint metadata only. The checkpoint body lives in the store.'''

    run = models.ForeignKey('automation.Run', on_delete=models.CASCADE, related_name='checkpoint_metadata')
    span = models.ForeignKey(
        'automation.ExecutionSpan',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='checkpoint_metadata',
    )
    thread_id = models.CharField(max_length=255, db_index=True)
    checkpoint_id = models.CharField(max_length=255, db_index=True)
    checkpoint_namespace = models.CharField(max_length=255, blank=True, default='')
    backend = models.CharField(max_length=100, default='memory')
    node_name = models.CharField(max_length=200, blank=True, default='')
    state_summary = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['run', 'thread_id']),
            models.Index(fields=['backend', 'node_name']),
        ]

    def __str__(self) -> str:
        return f'Checkpoint({self.pk}, {self.backend}, {self.checkpoint_id})'
