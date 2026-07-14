'''Django admin registrations for the automation control plane.'''

from __future__ import annotations

from django.contrib import admin

from langgraph_automation.apps.automation.models import Artifact, CheckpointMetadata, ExecutionSpan, Run, RunEvent, Workflow


@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'created_at', 'updated_at')
    search_fields = ('name', 'description')
    list_filter = ('created_at',)


@admin.register(Run)
class RunAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'workflow', 'status', 'thread_id', 'created_at', 'updated_at')
    list_filter = ('status', 'workflow')
    search_fields = ('name', 'thread_id')


@admin.register(ExecutionSpan)
class ExecutionSpanAdmin(admin.ModelAdmin):
    list_display = ('id', 'run', 'span_type', 'name', 'status', 'node_name', 'duration_ms', 'created_at')
    list_filter = ('span_type', 'status', 'node_name')
    search_fields = ('name', 'node_name', 'error_message')


@admin.register(RunEvent)
class RunEventAdmin(admin.ModelAdmin):
    list_display = ('id', 'run', 'event_type', 'level', 'node_name', 'created_at')
    list_filter = ('event_type', 'level', 'node_name')
    search_fields = ('message',)


@admin.register(Artifact)
class ArtifactAdmin(admin.ModelAdmin):
    list_display = ('id', 'run', 'name', 'kind', 'content_type', 'size', 'created_at')
    list_filter = ('kind', 'content_type')
    search_fields = ('name', 'storage_key')


@admin.register(CheckpointMetadata)
class CheckpointMetadataAdmin(admin.ModelAdmin):
    list_display = ('id', 'run', 'thread_id', 'checkpoint_id', 'backend', 'node_name', 'created_at')
    list_filter = ('backend', 'node_name')
    search_fields = ('thread_id', 'checkpoint_id')
