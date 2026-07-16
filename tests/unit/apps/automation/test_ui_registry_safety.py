"""UI registry safety tests."""

from __future__ import annotations

import pytest

from langgraph_automation.apps.automation.models.artifact import Artifact
from langgraph_automation.apps.automation.models.checkpoint import CheckpointMetadata
from langgraph_automation.apps.automation.models.event import RunEvent
from langgraph_automation.apps.automation.models.execution import ExecutionSpan, ExecutionSpanType
from langgraph_automation.apps.automation.models.run import Run
from langgraph_automation.apps.automation.models.workflow import Workflow
from langgraph_automation.apps.automation.ui.builders import build_detail_page_spec
from langgraph_automation.apps.automation.ui.registry import get_model_ui_config
from langgraph_automation.integrations.observability import DjangoEventSink


def test_ui_registry_visible_fields_use_safe_summary_names() -> None:
    forbidden = {'definition_payload', 'input_payload', 'output_payload', 'payload', 'metadata'}

    runs = get_model_ui_config('runs')
    workflows = get_model_ui_config('workflows')
    spans = get_model_ui_config('spans')
    events = get_model_ui_config('events')
    artifacts = get_model_ui_config('artifacts')
    checkpoints = get_model_ui_config('checkpoints')

    assert runs is not None
    assert workflows is not None
    assert spans is not None
    assert events is not None
    assert artifacts is not None
    assert checkpoints is not None

    for config in (runs, workflows, spans, events, artifacts, checkpoints):
        visible_fields = set(config.list_fields) | set(config.detail_fields)
        assert not (visible_fields & forbidden)

    assert 'definition_payload_summary' in workflows.detail_fields
    assert 'input_payload_summary' in runs.detail_fields
    assert 'output_payload_summary' in runs.detail_fields
    assert 'metadata_summary' in spans.detail_fields
    assert 'metrics_summary' in spans.detail_fields
    assert 'payload_summary' in events.detail_fields
    assert 'metadata_summary' in artifacts.detail_fields


@pytest.mark.django_db
def test_detail_page_specs_use_safe_summaries_for_raw_payload_fields() -> None:
    workflow = Workflow.objects.create(
        name='wf-ui-safe',
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
        name='run-ui-safe',
        input_payload={
            'text': 'summarize this /tmp/secret.txt Authorization: Bearer secret-token',
        },
    )
    sink = DjangoEventSink()
    graph_ref = sink.span_started(
        run.pk,
        ExecutionSpanType.GRAPH,
        'ui-graph',
        node_name='graph',
        metadata={'api_key': 'Authorization: Bearer secret-token /tmp/secret.txt'},
    )
    sink.span_completed(
        graph_ref,
        output_summary='Authorization: Bearer secret-token /tmp/secret.txt',
        metrics={'nested': {'path': '/tmp/secret.txt'}},
        metadata={'trace_id': 'Authorization: Bearer secret-token /tmp/secret.txt'},
    )
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

    run_spec = build_detail_page_spec('runs', run)
    workflow_spec = build_detail_page_spec('workflows', workflow)
    span_spec = build_detail_page_spec('spans', ExecutionSpan.objects.get(pk=graph_ref.span_id))
    event_spec = build_detail_page_spec('events', RunEvent.objects.get(pk=event.pk))
    artifact_spec = build_detail_page_spec('artifacts', Artifact.objects.get(pk=artifact.pk))
    checkpoint_spec = build_detail_page_spec('checkpoints', CheckpointMetadata.objects.get(pk=checkpoint.pk))

    run_fields = {field.name: field.display_value for field in run_spec.fields}
    workflow_fields = {field.name: field.display_value for field in workflow_spec.fields}
    span_fields = {field.name: field.display_value for field in span_spec.fields}
    event_fields = {field.name: field.display_value for field in event_spec.fields}
    artifact_fields = {field.name: field.display_value for field in artifact_spec.fields}
    checkpoint_fields = {field.name: field.display_value for field in checkpoint_spec.fields}

    assert 'secret-token' not in run_fields['input_payload_summary']
    assert '/tmp/secret.txt' not in run_fields['input_payload_summary']
    assert 'value_type' in run_fields['input_payload_summary']
    assert 'keys' in run_fields['input_payload_summary']

    assert 'secret-token' not in run_fields['output_payload_summary']
    assert '/tmp/secret.txt' not in run_fields['output_payload_summary']
    assert 'value_type' in run_fields['output_payload_summary']
    assert 'keys' in run_fields['output_payload_summary']

    assert 'secret-token' not in workflow_fields['definition_payload_summary']
    assert '/tmp/secret.txt' not in workflow_fields['definition_payload_summary']
    assert 'value_type' in workflow_fields['definition_payload_summary']
    assert 'keys' in workflow_fields['definition_payload_summary']

    assert 'secret-token' not in span_fields['metadata_summary']
    assert '/tmp/secret.txt' not in span_fields['metadata_summary']
    assert 'secret-token' not in span_fields['metrics_summary']
    assert '/tmp/secret.txt' not in span_fields['metrics_summary']

    assert 'secret-token' not in event_fields['payload_summary']
    assert '/tmp/secret.txt' not in event_fields['payload_summary']

    assert 'secret-token' not in artifact_fields['metadata_summary']
    assert '/tmp/secret.txt' not in artifact_fields['metadata_summary']

    assert 'secret-token' not in checkpoint_fields['state_summary']
    assert '/tmp/secret.txt' not in checkpoint_fields['state_summary']
