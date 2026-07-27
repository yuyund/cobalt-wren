"""Admin exposure safety tests."""

from __future__ import annotations

from django.contrib import admin
from django.test import RequestFactory
import pytest

from cobalt_wren.apps.automation.admin import (
    ArtifactAdmin,
    CheckpointMetadataAdmin,
    ExecutionSpanAdmin,
    RunAdmin,
    RunEventAdmin,
    WorkflowAdmin,
)
from cobalt_wren.apps.automation.models.artifact import Artifact
from cobalt_wren.apps.automation.models.checkpoint import CheckpointMetadata
from cobalt_wren.apps.automation.models.event import RunEvent
from cobalt_wren.apps.automation.models.execution import ExecutionSpan, ExecutionSpanType
from cobalt_wren.apps.automation.models.run import Run
from cobalt_wren.apps.automation.models.workflow import Workflow
from cobalt_wren.integrations.observability import DjangoEventSink


@pytest.mark.django_db
def test_run_and_workflow_admins_hide_raw_payload_fields_and_show_safe_summaries() -> None:
    request = RequestFactory().get('/admin/')
    run_admin = admin.site._registry[Run]
    workflow_admin = admin.site._registry[Workflow]

    assert isinstance(run_admin, RunAdmin)
    assert isinstance(workflow_admin, WorkflowAdmin)

    run_fields = run_admin.get_fields(request)
    workflow_fields = workflow_admin.get_fields(request)

    assert 'input_payload' not in run_fields
    assert 'output_payload' not in run_fields
    assert 'definition_payload' not in workflow_fields
    assert 'input_payload_summary' in run_fields
    assert 'output_payload_summary' in run_fields
    assert 'definition_payload_summary' in workflow_fields

    workflow = Workflow.objects.create(
        name='wf-admin-safe',
        description='safe workflow',
        definition_payload={
            'llm': {
                'api_key': 'Authorization: Bearer secret-token /tmp/secret.txt',
            },
            'graph': {
                'kind': 'llm_echo_summary',
            },
        },
    )
    run = Run.objects.create(
        workflow=workflow,
        name='run-admin-safe',
        input_payload={
            'text': 'summarize this /tmp/secret.txt Authorization: Bearer secret-token',
        },
    )

    run_summary = run_admin.input_payload_summary(run)
    run_output_summary = run_admin.output_payload_summary(run)
    workflow_summary = workflow_admin.definition_payload_summary(workflow)

    assert 'secret-token' not in str(run_summary)
    assert '/tmp/secret.txt' not in str(run_summary)
    assert 'secret-token' not in str(run_output_summary)
    assert '/tmp/secret.txt' not in str(run_output_summary)
    assert 'secret-token' not in str(workflow_summary)
    assert '/tmp/secret.txt' not in str(workflow_summary)


@pytest.mark.django_db
def test_span_event_artifact_and_checkpoint_admins_show_safe_summary_fields_only() -> None:
    request = RequestFactory().get('/admin/')
    run_admin = admin.site._registry[Run]
    span_admin = admin.site._registry[ExecutionSpan]
    event_admin = admin.site._registry[RunEvent]
    artifact_admin = admin.site._registry[Artifact]
    checkpoint_admin = admin.site._registry[CheckpointMetadata]

    assert isinstance(run_admin, RunAdmin)
    assert isinstance(span_admin, ExecutionSpanAdmin)
    assert isinstance(event_admin, RunEventAdmin)
    assert isinstance(artifact_admin, ArtifactAdmin)
    assert isinstance(checkpoint_admin, CheckpointMetadataAdmin)

    run_fields = run_admin.get_fields(request)
    span_fields = span_admin.get_fields(request)
    event_fields = event_admin.get_fields(request)
    artifact_fields = artifact_admin.get_fields(request)
    checkpoint_fields = checkpoint_admin.get_fields(request)

    assert 'metadata' not in span_fields
    assert 'metrics' not in span_fields
    assert 'payload' not in event_fields
    assert 'metadata' not in artifact_fields
    assert 'input_payload' not in run_fields
    assert 'output_payload' not in run_fields
    assert 'state_summary' in checkpoint_fields

    workflow = Workflow.objects.create(name='wf-admin-observability')
    run = Run.objects.create(
        workflow=workflow,
        name='run-admin-observability',
        input_payload={'text': 'Authorization: Bearer secret-token /tmp/secret.txt'},
        output_payload={'summary': 'done', 'secret': 'Authorization: Bearer secret-token /tmp/secret.txt'},
    )
    sink = DjangoEventSink()
    graph_ref = sink.span_started(run.pk, ExecutionSpanType.GRAPH, 'graph-span', node_name='graph', metadata={'api_key': 'Authorization: Bearer secret-token /tmp/secret.txt'})
    sink.span_completed(graph_ref, output_summary='Authorization: Bearer secret-token /tmp/secret.txt', metrics={'nested': {'path': '/tmp/secret.txt'}}, metadata={'trace_id': 'Authorization: Bearer secret-token /tmp/secret.txt'})
    event = sink.semantic_event(
        run.pk,
        'planner.decision_made',
        message='planner selected route',
        payload={'token': 'Authorization: Bearer secret-token /tmp/secret.txt'},
        parent_span=graph_ref,
        node_name='planner',
    )
    artifact = sink.artifact_created(
        run.pk,
        'artifact-1',
        'report',
        'text',
        metadata={'trace_id': 'Authorization: Bearer secret-token /tmp/secret.txt'},
    )
    checkpoint = sink.checkpoint_saved(
        run.pk,
        'thread-1',
        'checkpoint-1',
        'sqlite',
        state_summary='Authorization: Bearer secret-token /tmp/secret.txt',
    )

    span = ExecutionSpan.objects.get(pk=graph_ref.span_id)
    event = RunEvent.objects.get(pk=event.pk)
    artifact = Artifact.objects.get(pk=artifact.pk)
    checkpoint = CheckpointMetadata.objects.get(pk=checkpoint.pk)

    assert 'value_type' in span_admin.metadata_summary(span)
    assert 'value_type' in span_admin.metrics_summary(span)
    assert 'secret-token' not in span_admin.metadata_summary(span)
    assert 'secret-token' not in span_admin.metrics_summary(span)
    assert 'value_type' in event_admin.payload_summary(event)
    assert 'secret-token' not in event_admin.payload_summary(event)
    assert 'value_type' in artifact_admin.metadata_summary(artifact)
    assert 'secret-token' not in artifact_admin.metadata_summary(artifact)
    assert 'secret-token' not in checkpoint.state_summary
