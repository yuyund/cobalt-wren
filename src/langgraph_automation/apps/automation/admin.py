'''Django admin registrations for the automation control plane.'''

from __future__ import annotations

from django.contrib import admin

from langgraph_automation.apps.automation.models import Artifact, CheckpointMetadata, ExecutionSpan, OperationAuditLog, Run, RunEvent, Workflow
from langgraph_automation.apps.automation.ui.formatters import format_value
from langgraph_automation.core.summary import summarize_display_value


@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'created_at', 'updated_at')
    search_fields = ('name', 'description')
    list_filter = ('created_at',)
    readonly_fields = ('definition_payload_summary', 'created_at', 'updated_at')

    def get_fields(self, request, obj=None):
        del request, obj
        return ('name', 'description', 'definition_payload_summary', 'created_at', 'updated_at')

    @admin.display(description='Definition payload summary')
    def definition_payload_summary(self, obj: Workflow) -> object:
        return format_value(summarize_display_value(obj.definition_payload))


@admin.register(Run)
class RunAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'workflow', 'status', 'thread_id', 'created_at', 'updated_at')
    list_filter = ('status', 'workflow')
    search_fields = ('name', 'thread_id')
    readonly_fields = (
        'input_payload_summary',
        'output_payload_summary',
        'error_message',
        'started_at',
        'finished_at',
        'last_event_at',
        'last_span_name',
        'created_at',
        'updated_at',
    )

    def get_fields(self, request, obj=None):
        del request, obj
        return (
            'workflow',
            'name',
            'status',
            'thread_id',
            'input_payload_summary',
            'output_payload_summary',
            'error_message',
            'started_at',
            'finished_at',
            'last_event_at',
            'last_span_name',
            'created_at',
            'updated_at',
        )

    @admin.display(description='Input payload summary')
    def input_payload_summary(self, obj: Run) -> object:
        return format_value(summarize_display_value(obj.input_payload))

    @admin.display(description='Output payload summary')
    def output_payload_summary(self, obj: Run) -> object:
        return format_value(summarize_display_value(obj.output_payload))


@admin.register(ExecutionSpan)
class ExecutionSpanAdmin(admin.ModelAdmin):
    list_display = ('id', 'run', 'span_type', 'name', 'status', 'node_name', 'duration_ms', 'created_at')
    list_filter = ('span_type', 'status', 'node_name')
    search_fields = ('name', 'node_name', 'error_message')
    readonly_fields = (
        'run',
        'parent',
        'span_type',
        'name',
        'status',
        'node_name',
        'attempt',
        'started_at',
        'finished_at',
        'duration_ms',
        'input_summary',
        'output_summary',
        'error_message',
        'metrics_summary',
        'metadata_summary',
        'external_trace_id',
        'external_span_id',
        'created_at',
        'updated_at',
    )

    def get_fields(self, request, obj=None):
        del request, obj
        return (
            'run',
            'parent',
            'span_type',
            'name',
            'status',
            'node_name',
            'attempt',
            'started_at',
            'finished_at',
            'duration_ms',
            'input_summary',
            'output_summary',
            'error_message',
            'metrics_summary',
            'metadata_summary',
            'external_trace_id',
            'external_span_id',
            'created_at',
            'updated_at',
        )

    @admin.display(description='Metrics summary')
    def metrics_summary(self, obj: ExecutionSpan) -> object:
        return format_value(summarize_display_value(obj.metrics))

    @admin.display(description='Metadata summary')
    def metadata_summary(self, obj: ExecutionSpan) -> object:
        return format_value(summarize_display_value(obj.metadata))


@admin.register(RunEvent)
class RunEventAdmin(admin.ModelAdmin):
    list_display = ('id', 'run', 'event_type', 'level', 'node_name', 'created_at')
    list_filter = ('event_type', 'level', 'node_name')
    search_fields = ('message',)
    readonly_fields = ('run', 'span', 'event_type', 'level', 'node_name', 'message', 'payload_summary', 'created_at')

    def get_fields(self, request, obj=None):
        del request, obj
        return ('run', 'span', 'event_type', 'level', 'node_name', 'message', 'payload_summary', 'created_at')

    @admin.display(description='Payload summary')
    def payload_summary(self, obj: RunEvent) -> object:
        return format_value(summarize_display_value(obj.payload))


@admin.register(Artifact)
class ArtifactAdmin(admin.ModelAdmin):
    list_display = ('id', 'run', 'name', 'kind', 'content_type', 'size', 'created_at')
    list_filter = ('kind', 'content_type')
    search_fields = ('name', 'storage_key')
    readonly_fields = ('run', 'span', 'name', 'kind', 'storage_key', 'content_type', 'size', 'metadata_summary', 'created_at')

    def get_fields(self, request, obj=None):
        del request, obj
        return ('run', 'span', 'name', 'kind', 'storage_key', 'content_type', 'size', 'metadata_summary', 'created_at')

    @admin.display(description='Metadata summary')
    def metadata_summary(self, obj: Artifact) -> object:
        return format_value(summarize_display_value(obj.metadata))


@admin.register(CheckpointMetadata)
class CheckpointMetadataAdmin(admin.ModelAdmin):
    list_display = ('id', 'run', 'thread_id', 'checkpoint_id', 'backend', 'node_name', 'created_at')
    list_filter = ('backend', 'node_name')
    search_fields = ('thread_id', 'checkpoint_id')
    readonly_fields = ('run', 'span', 'thread_id', 'checkpoint_id', 'checkpoint_namespace', 'backend', 'node_name', 'state_summary', 'created_at')

    def get_fields(self, request, obj=None):
        del request, obj
        return ('run', 'span', 'thread_id', 'checkpoint_id', 'checkpoint_namespace', 'backend', 'node_name', 'state_summary', 'created_at')


@admin.register(OperationAuditLog)
class OperationAuditLogAdmin(admin.ModelAdmin):
    list_display = ("id", "created_at", "actor_identifier", "action", "target_type", "target_id", "outcome")
    list_filter = ("action", "outcome", "target_type")
    search_fields = ("actor_identifier", "target_id", "message")
    readonly_fields = ("actor_identifier", "action", "target_type", "target_id", "run", "outcome", "safe_payload_summary", "message", "created_at")
