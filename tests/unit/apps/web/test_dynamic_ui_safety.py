"""Dynamic UI safety tests."""

from __future__ import annotations

import pytest
from django.urls import reverse

from langgraph_automation.apps.automation.models.artifact import Artifact
from langgraph_automation.apps.automation.models.checkpoint import CheckpointMetadata
from langgraph_automation.apps.automation.models.event import RunEvent
from langgraph_automation.apps.automation.models.execution import ExecutionSpan, ExecutionSpanType
from langgraph_automation.apps.automation.models.run import Run
from langgraph_automation.apps.automation.models.workflow import Workflow
from langgraph_automation.apps.automation.services import runtime as runtime_module
from langgraph_automation.integrations.observability import DjangoEventSink


@pytest.mark.django_db
def test_dynamic_detail_views_do_not_render_raw_payload_content(client) -> None:
    workflow = Workflow.objects.create(
        name='wf-dynamic-safe',
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
        name='run-dynamic-safe',
        input_payload={
            'text': 'summarize this /tmp/secret.txt Authorization: Bearer secret-token',
        },
    )

    run_response = client.get(reverse('dynamic-detail', kwargs={'model_key': 'runs', 'object_id': run.pk}))
    workflow_response = client.get(reverse('dynamic-detail', kwargs={'model_key': 'workflows', 'object_id': workflow.pk}))

    assert run_response.status_code == 200
    assert workflow_response.status_code == 200

    run_html = run_response.content.decode()
    workflow_html = workflow_response.content.decode()

    for html in (run_html, workflow_html):
        assert 'secret-token' not in html
        assert '/tmp/secret.txt' not in html
        assert 'Authorization: Bearer' not in html
        assert 'value_type' in html or 'keys' in html


@pytest.mark.django_db
def test_dynamic_list_form_action_and_fragment_views_do_not_render_raw_payload_content(
    client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_completion(*_args, **_kwargs):
        return {
            'choices': [
                {
                    'message': {'content': 'final summary'},
                    'finish_reason': 'stop',
                }
            ],
            'usage': {
                'prompt_tokens': 3,
                'completion_tokens': 2,
            },
            'model': 'fake-provider-model',
        }

    sink = DjangoEventSink()
    monkeypatch.setattr(runtime_module, 'build_event_sink', lambda _run: sink)
    monkeypatch.setattr('langgraph_automation.integrations.llm.litellm_client.litellm.completion', fake_completion)

    workflow = Workflow.objects.create(
        name='wf-dynamic-safe-2',
        description='safe workflow',
        definition_payload={
            'workflow': {'kind': 'reference.llm_echo_summary'},
            'llm': {'enabled': True, 'model': 'test-model'},
            'tools': {'allowed': ['echo']},
        },
    )
    run = Run.objects.create(
        workflow=workflow,
        name='run-dynamic-safe-2',
        input_payload={'text': 'summarize this /tmp/secret.txt Authorization: Bearer secret-token'},
    )

    graph_ref = sink.span_started(
        run.pk,
        ExecutionSpanType.GRAPH,
        'dynamic-graph',
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

    list_response = client.get(reverse('dynamic-list', kwargs={'model_key': 'runs'}))
    detail_response = client.get(reverse('dynamic-detail', kwargs={'model_key': 'runs', 'object_id': run.pk}))
    form_response = client.get(reverse('dynamic-edit', kwargs={'model_key': 'runs', 'object_id': run.pk}))
    action_response = client.post(reverse('dynamic-action', kwargs={'model_key': 'runs', 'object_id': run.pk, 'action_name': 'start'}))
    fragment_responses = [
        client.get(reverse('dynamic-fragment', kwargs={'model_key': 'runs', 'object_id': run.pk, 'fragment_name': fragment}))
        for fragment in ('spans', 'events', 'artifacts', 'checkpoints')
    ]

    assert list_response.status_code == 200
    assert detail_response.status_code == 200
    assert form_response.status_code == 200
    assert action_response.status_code == 200
    for response in fragment_responses:
        assert response.status_code == 200

    html_bodies = [
        response.content.decode()
        for response in (list_response, detail_response, form_response, action_response, *fragment_responses)
    ]
    for html in html_bodies:
        assert 'secret-token' not in html
        assert '/tmp/secret.txt' not in html
        assert 'Authorization: Bearer' not in html
        assert 'Traceback' not in html

    assert 'Run' in detail_response.content.decode()
    assert 'Execution Spans' in detail_response.content.decode() or 'No spans yet' in detail_response.content.decode()

    span = ExecutionSpan.objects.get(pk=graph_ref.span_id)
    event_row = RunEvent.objects.get(pk=event.pk)
    artifact_row = Artifact.objects.get(pk=artifact.pk)
    checkpoint_row = CheckpointMetadata.objects.get(pk=checkpoint.pk)
    assert str(span.pk) == graph_ref.span_id
    assert event_row.pk == event.pk
    assert artifact_row.pk == artifact.pk
    assert checkpoint_row.pk == checkpoint.pk
