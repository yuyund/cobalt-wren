"""Unit tests for the llm_echo_summary reference diagnostic workflow nodes."""

from __future__ import annotations

import logging

import pytest

from langgraph_automation.apps.automation.services.workflow_config import WorkflowRuntimeConfig
from langgraph_automation.core.errors import MissingRuntimeDependencyError
from langgraph_automation.graphs.inputs import GraphExecutionInput
from langgraph_automation.workflows.reference.llm_echo_summary.nodes import echo_tool_node, llm_summary_node
from langgraph_automation.graphs.runtime import GraphRuntime
from langgraph_automation.integrations.llm.base import LLMResult
from langgraph_automation.integrations.llm.observed_client import ObservedLLMClient
from langgraph_automation.integrations.observability.types import ObservabilityContext
from langgraph_automation.integrations.tools.base import ToolResult
from langgraph_automation.integrations.tools.observed_registry import ObservedToolRegistry
from langgraph_automation.integrations.tools.registry import InMemoryToolRegistry
from tests.support.llm_doubles import RecordingLLMClient
from tests.support.recording_event_sink import RecordingEventSink
from tests.support.tool_doubles import RecordingToolCallable


def test_echo_tool_node_uses_runtime_tool_registry_and_saves_summary() -> None:
    sink = RecordingEventSink()
    calls: list[dict[str, object]] = []
    inner_registry = InMemoryToolRegistry()
    inner_registry.register(
        'echo',
        RecordingToolCallable(
            result=ToolResult(
                output='raw secret /tmp/secret.txt',
                output_summary='bounded summary',
                exit_code=0,
                metadata={'tool_name': 'echo'},
            ),
            calls=calls,
        ),
    )
    runtime = GraphRuntime(
        logger=logging.getLogger('test.nodes.echo'),
        observability=ObservabilityContext(run_id=1, thread_id='thread-1'),
        workflow_config=WorkflowRuntimeConfig(),
        event_sink=sink,
        tool_registry=ObservedToolRegistry(inner=inner_registry, event_sink=sink, observability=ObservabilityContext(run_id=1, thread_id='thread-1')),
        execution_input=GraphExecutionInput(text='summarize this /tmp/secret.txt'),
    )

    result = echo_tool_node({'input_summary': {'keys': ['text']}}, runtime)

    assert calls == [{'text': 'summarize this /tmp/secret.txt'}]
    assert result['current_node'] == 'echo'
    assert result['echo']['status'] == 'succeeded'
    assert result['echo']['output_summary'] == 'bounded summary'
    assert result['output_payload']['echo']['status'] == 'succeeded'
    assert 'raw secret' not in str(result)


def test_llm_summary_node_uses_runtime_llm_client_and_returns_safe_summary() -> None:
    sink = RecordingEventSink()
    inner_client = RecordingLLMClient(
        result=LLMResult(
            content='safe summary',
            raw={'provider_response': 'hidden', 'authorization': 'Bearer secret'},
            provider='fake-provider',
            model='fake-model',
            input_tokens=4,
            output_tokens=2,
        )
    )
    runtime = GraphRuntime(
        logger=logging.getLogger('test.nodes.llm'),
        observability=ObservabilityContext(run_id=2, thread_id='thread-2'),
        workflow_config=WorkflowRuntimeConfig(),
        event_sink=sink,
        llm_client=ObservedLLMClient(inner=inner_client, event_sink=sink, observability=ObservabilityContext(run_id=2, thread_id='thread-2')),
        execution_input=GraphExecutionInput(prompt='summarize /tmp/secret.txt Authorization: Bearer secret-token'),
    )

    result = llm_summary_node(
        {
            'input_summary': {'keys': ['prompt']},
            'echo': {'status': 'succeeded', 'output_summary': 'bounded summary'},
        },
        runtime,
    )

    assert len(inner_client.calls) == 1
    messages = inner_client.calls[0].messages
    assert messages[0]['role'] == 'system'
    assert 'Summarize the user input concisely' in messages[0]['content']
    assert messages[1]['role'] == 'system'
    assert messages[2]['role'] == 'user'
    assert messages[2]['content'] == 'summarize /tmp/secret.txt Authorization: Bearer secret-token'
    assert result['current_node'] == 'llm_summary'
    assert result['output_payload']['summary'] == 'safe summary'
    assert result['output_payload']['llm']['provider'] == 'fake-provider'
    assert result['output_payload']['llm']['model'] == 'fake-model'
    assert 'provider_response' not in str(result)


def test_nodes_require_runtime_dependencies() -> None:
    runtime = GraphRuntime(logger=logging.getLogger('test.nodes.missing'), workflow_config=WorkflowRuntimeConfig())

    with pytest.raises(MissingRuntimeDependencyError):
        echo_tool_node({'input_summary': {'keys': ['text']}}, runtime)

    with pytest.raises(MissingRuntimeDependencyError):
        llm_summary_node({'input_summary': {'keys': ['text']}}, runtime)
