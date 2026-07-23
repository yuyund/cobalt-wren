'''Workflow model for the Django control plane.'''

from __future__ import annotations

from django.db import models

from langgraph_automation.core.summary import summarize_display_value


class Workflow(models.Model):
    '''Definition and configuration for a LangGraph workflow.'''

    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True, default='')
    definition_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return self.name

    @property
    def definition_payload_summary(self) -> object:
        return summarize_display_value(self.definition_payload)
