'''Artifact model for control plane metadata.'''

from __future__ import annotations

from django.db import models

from langgraph_automation.core.summary import summarize_display_value
from langgraph_automation.integrations.artifact.keys import validate_storage_key


class Artifact(models.Model):
    '''Artifact metadata. The actual content lives in an external store.'''

    run = models.ForeignKey('automation.Run', on_delete=models.CASCADE, related_name='artifacts')
    span = models.ForeignKey(
        'automation.ExecutionSpan',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='artifacts',
    )
    name = models.CharField(max_length=200)
    kind = models.CharField(max_length=100)
    storage_key = models.CharField(max_length=500)
    content_type = models.CharField(max_length=100, blank=True, default='')
    size = models.PositiveBigIntegerField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['run', 'kind']),
            models.Index(fields=['run', 'name']),
        ]

    def __str__(self) -> str:
        return f'Artifact({self.pk}, {self.kind}, {self.name})'

    def clean(self) -> None:
        super().clean()
        self.storage_key = validate_storage_key(self.storage_key)

    @property
    def metadata_summary(self) -> object:
        return summarize_display_value(self.metadata)
