"""Service-level tests for the minimal LLM + EchoTool workflow."""

from __future__ import annotations

import pytest

from langgraph_automation.apps.automation.models.run import Run, RunStatus
from langgraph_automation.apps.automation.models.workflow import Workflow
from langgraph_automation.apps.automation.services import runs as run_services
from langgraph_automation.apps.automation.services import runtime as runtime_module
from langgraph_automation.core.result_safety import safe_run_error_message, safe_run_output_payload
from tests.support.recording_event_sink import RecordingEventSink


def _fake_litellm_completion(**_kwargs):
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


@pytest.mark.django_db
def test_start_run_executes_minimal_llm_workflow_and_saves_safe_output(monkeypatch: pytest.MonkeyPatch) -> None:
    sink = RecordingEventSink()
    monkeypatch.setattr(runtime_module, 'build_event_sink', lambda _run: sink)
    monkeypatch.setattr('langgraph_automation.integrations.llm.litellm_client.litellm.completion', _fake_litellm_completion)

    workflow = Workflow.objects.create(
        name='wf-minimal-llm',
        definition_payload={
            'graph': {'kind': 'llm_echo_summary'},
            'llm': {
                'enabled': True,
                'model': 'test-model',
                'temperature': 0.2,
                'max_tokens': 512,
            },
            'tools': {
                'allowed': ['echo'],
            },
        },
    )
    run = Run.objects.create(
        workflow=workflow,
        name='run-minimal-llm',
        input_payload={'text': 'summarize this /tmp/secret.txt Authorization: Bearer secret-token'},
    )

    result = run_services.start_run(run=run)
    result.run.refresh_from_db()

    assert result.run.status == RunStatus.SUCCEEDED
    assert result.run.error_message == ''
    assert result.execution_result is not None
    assert result.execution_result.output_payload['summary'] == 'final summary'
    assert result.execution_result.output_payload['echo']['status'] == 'succeeded'
    assert result.execution_result.output_payload['llm']['provider'] == 'litellm'
    assert result.run.output_payload == safe_run_output_payload(result.execution_result.output_payload)
    assert 'secret-token' not in repr(result.run.output_payload)
    assert '/tmp/secret.txt' not in repr(result.run.output_payload)

    assert sink.run_events[0].kind == 'run.started'
    assert sink.run_events[-1].kind == 'run.completed'
    assert any(span.span_type == 'tool' and span.status == 'succeeded' for span in sink.spans.values())
    assert any(span.span_type == 'llm' and span.status == 'succeeded' for span in sink.spans.values())


@pytest.mark.django_db
def test_start_run_keeps_workflow_running_when_echo_is_policy_denied(monkeypatch: pytest.MonkeyPatch) -> None:
    sink = RecordingEventSink()
    monkeypatch.setattr(runtime_module, 'build_event_sink', lambda _run: sink)
    monkeypatch.setattr('langgraph_automation.integrations.llm.litellm_client.litellm.completion', _fake_litellm_completion)

    workflow = Workflow.objects.create(
        name='wf-minimal-llm-denied',
        definition_payload={
            'graph': {'kind': 'llm_echo_summary'},
            'llm': {
                'enabled': True,
                'model': 'test-model',
            },
        },
    )
    run = Run.objects.create(
        workflow=workflow,
        name='run-minimal-llm-denied',
        input_payload={'prompt': 'summarize this /tmp/secret.txt'},
    )

    result = run_services.start_run(run=run)
    result.run.refresh_from_db()

    assert result.run.status == RunStatus.SUCCEEDED
    assert result.execution_result is not None
    assert result.execution_result.output_payload['echo']['status'] == 'denied'
    assert result.run.output_payload == safe_run_output_payload(result.execution_result.output_payload)
    assert sink.spans[next(span_id for span_id, span in sink.spans.items() if span.span_type == 'tool')].status == 'failed'


@pytest.mark.django_db
def test_start_run_fails_when_llm_is_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    sink = RecordingEventSink()
    monkeypatch.setattr(runtime_module, 'build_event_sink', lambda _run: sink)

    workflow = Workflow.objects.create(
        name='wf-minimal-llm-disabled',
        definition_payload={
            'graph': {'kind': 'llm_echo_summary'},
            'llm': {
                'enabled': False,
            },
            'tools': {
                'allowed': ['echo'],
            },
        },
    )
    run = Run.objects.create(
        workflow=workflow,
        name='run-minimal-llm-disabled',
        input_payload={'text': 'summarize this'},
    )

    result = run_services.start_run(run=run)
    result.run.refresh_from_db()

    assert result.run.status == RunStatus.FAILED
    assert result.run.error_message == safe_run_error_message(result.execution_result.error_message)
    assert 'LLM client is not configured' in result.run.error_message
    assert result.run.output_payload == safe_run_output_payload(result.execution_result.output_payload)
    assert any(span.span_type == 'node' and span.name == 'llm_summary' and span.status == 'failed' for span in sink.spans.values())
    assert any(span.span_type == 'graph' and span.status == 'failed' for span in sink.spans.values())
