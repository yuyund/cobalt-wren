"""Service-level tests for the llm_echo_summary reference diagnostic workflow."""

from __future__ import annotations


import pytest

from langgraph_automation.apps.automation.models.run import Run, RunStatus
from langgraph_automation.apps.automation.models.workflow import Workflow
from langgraph_automation.apps.automation.services import runs as run_services
from langgraph_automation.apps.automation.services import runtime as runtime_module
from langgraph_automation.core.result_safety import safe_run_output_payload
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
    services = runtime_module.build_run_execution_services_from_mapping({
        'version': 1,
        'providers': {'default': {'provider': 'litellm', 'model': 'test-model'}},
        'tools': {'allowlist': ['echo']},
    })

    workflow = Workflow.objects.create(
        name='wf-minimal-llm',
        definition_payload={
            'workflow': {'kind': 'reference.llm_echo_summary', 'config': {'allowed_tools': ['echo']}},
        },
    )
    run = Run.objects.create(
        workflow=workflow,
        name='run-minimal-llm',
        input_payload={'text': 'summarize this /tmp/secret.txt Authorization: Bearer secret-token'},
    )

    result = run_services.start_run(run=run, services=services)
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
