"""Service-level tests for the llm_echo_summary reference diagnostic workflow."""

from __future__ import annotations

import logging

import pytest

from langgraph_automation.apps.automation.models.run import Run, RunStatus
from langgraph_automation.apps.automation.models.workflow import Workflow
from langgraph_automation.apps.automation.services import runs as run_services
from langgraph_automation.apps.automation.services import runtime as runtime_module
from langgraph_automation.apps.automation.services.workflow_config import GraphWorkflowConfig, MINIMAL_GRAPH_KIND, WorkflowRuntimeConfig
from langgraph_automation.core.result_safety import safe_run_output_payload
from langgraph_automation.graphs.runtime import GraphRuntime
from langgraph_automation.workflows.catalog import build_builtin_graph_registry
from langgraph_automation.integrations.llm.base import LLMResult
from langgraph_automation.integrations.llm.observed_client import ObservedLLMClient
from langgraph_automation.integrations.observability.types import ObservabilityContext
from langgraph_automation.integrations.tools.base import ToolResult
from langgraph_automation.integrations.tools.observed_registry import ObservedToolRegistry
from langgraph_automation.integrations.tools.policy import AllowlistToolPolicy, ToolPolicyContext
from langgraph_automation.integrations.tools.policy_registry import PolicyAwareToolRegistry
from langgraph_automation.integrations.tools.registry import InMemoryToolRegistry
from langgraph_automation.integrations.tools.safe_tools import ECHO_TOOL_NAME
from tests.support.llm_doubles import RecordingLLMClient
from tests.support.recording_event_sink import RecordingEventSink
from tests.support.tool_doubles import RecordingToolCallable


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
    services = runtime_module.build_run_execution_services_from_mapping({'version': 1})

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


@pytest.mark.django_db
def test_start_run_continues_when_echo_is_policy_denied() -> None:
    sink = RecordingEventSink()
    inner_llm_client = RecordingLLMClient(
        result=LLMResult(content='final summary', provider='fake-provider', model='fake-model', input_tokens=1, output_tokens=1, raw={'provider_response': 'hidden'})
    )
    inner_registry = InMemoryToolRegistry()
    inner_registry.register(
        ECHO_TOOL_NAME,
        RecordingToolCallable(
            result=ToolResult(
                output='raw echo output /tmp/secret.txt',
                output_summary='echo summary',
                exit_code=0,
                metadata={'tool_name': ECHO_TOOL_NAME},
            )
        ),
    )
    runtime = GraphRuntime(
        logger=logging.getLogger('test.graph.minimal.denied'),
        observability=ObservabilityContext(run_id=2, thread_id='thread-2'),
        workflow_config=WorkflowRuntimeConfig(graph=GraphWorkflowConfig(kind=MINIMAL_GRAPH_KIND)),
        graph_registry=build_builtin_graph_registry(),
        event_sink=sink,
        llm_client=ObservedLLMClient(
            inner=inner_llm_client,
            event_sink=sink,
            observability=ObservabilityContext(run_id=2, thread_id='thread-2'),
        ),
        tool_registry=ObservedToolRegistry(
            inner=PolicyAwareToolRegistry(
                inner=inner_registry,
                policy=AllowlistToolPolicy(allowed_tools=frozenset()),
                context=ToolPolicyContext(run_id=2, workflow_id=99, thread_id='thread-2'),
            ),
            event_sink=sink,
            observability=ObservabilityContext(run_id=2, thread_id='thread-2'),
        ),
    )
    workflow = Workflow.objects.create(name='wf-minimal-denied')
    run = Run.objects.create(workflow=workflow, name='run-minimal-denied', input_payload={'text': 'summarize this'})

    result = run_services.start_run(run=run, runtime=runtime)
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
    services = runtime_module.build_run_execution_services_from_mapping({'version': 1})

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

    result = run_services.start_run(run=run, services=services)
    result.run.refresh_from_db()

    assert result.run.status == RunStatus.FAILED
    assert result.execution_result is not None
    assert 'requires llm.enabled=true' in result.run.error_message
    assert result.run.output_payload == {}
    assert sink.run_events[-1].kind == 'run.failed'
    assert result.execution_result.details['reason'] == 'workflow_configuration_error'
