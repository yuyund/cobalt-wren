"""Execution dispatch tests."""

from __future__ import annotations

import pytest

from langgraph_automation.apps.automation.models.run import Run
from langgraph_automation.apps.automation.models.workflow import Workflow
from langgraph_automation.apps.automation.services import runtime as runtime_module
from langgraph_automation.apps.automation.services.execution import dispatch_run_execution
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
def test_dispatch_run_execution_returns_normalized_result(monkeypatch: pytest.MonkeyPatch) -> None:
    sink = RecordingEventSink()
    monkeypatch.setattr(runtime_module, 'build_event_sink', lambda _run: sink)
    monkeypatch.setattr('langgraph_automation.integrations.llm.litellm_client.litellm.completion', _fake_litellm_completion)

    workflow = Workflow.objects.create(
        name='wf-dispatch',
        definition_payload={
            'graph': {'kind': 'llm_echo_summary'},
            'llm': {
                'enabled': True,
                'model': 'test-model',
            },
            'tools': {
                'allowed': ['echo'],
            },
        },
    )
    run = Run.objects.create(workflow=workflow, name='run-dispatch', input_payload={'text': 'summarize this'})

    runtime = runtime_module.build_graph_runtime(run)
    result = dispatch_run_execution(run, runtime=runtime)

    assert result.status == 'succeeded'
    assert result.output_payload['summary'] == 'final summary'
    assert result.output_payload['echo']['status'] == 'succeeded'
    assert result.output_payload['llm']['provider'] == 'litellm'
    assert result.last_node_name == 'llm_summary'
