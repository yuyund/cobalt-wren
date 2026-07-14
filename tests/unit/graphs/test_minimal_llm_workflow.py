"""Integration tests for the minimal LLM + EchoTool LangGraph workflow."""

from __future__ import annotations

import logging

from langgraph_automation.apps.automation.services.workflow_config import GraphWorkflowConfig, WorkflowRuntimeConfig, MINIMAL_GRAPH_KIND
from langgraph_automation.graphs.runner import LangGraphRunner
from langgraph_automation.graphs.runtime import GraphRuntime
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


def test_minimal_llm_workflow_runs_end_to_end_and_records_spans() -> None:
    sink = RecordingEventSink()
    inner_llm_client = RecordingLLMClient(
        result=LLMResult(
            content='final summary',
            raw={'provider_response': 'hidden', 'authorization': 'Bearer secret'},
            provider='fake-provider',
            model='fake-model',
            input_tokens=3,
            output_tokens=2,
        )
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
        logger=logging.getLogger('test.graph.minimal'),
        observability=ObservabilityContext(run_id=1, thread_id='thread-1'),
        workflow_config=WorkflowRuntimeConfig(graph=GraphWorkflowConfig(kind=MINIMAL_GRAPH_KIND)),
        event_sink=sink,
        llm_client=ObservedLLMClient(inner=inner_llm_client, event_sink=sink, observability=ObservabilityContext(run_id=1, thread_id='thread-1')),
        tool_registry=ObservedToolRegistry(inner=inner_registry, event_sink=sink, observability=ObservabilityContext(run_id=1, thread_id='thread-1')),
    )

    result = LangGraphRunner().run_graph_once(
        run_id=1,
        runtime=runtime,
        input_payload={'text': 'summarize this /tmp/secret.txt Authorization: Bearer token'},
    )

    assert result.status == 'succeeded'
    assert result.last_node_name == 'llm_summary'
    assert result.output_payload['summary'] == 'final summary'
    assert result.output_payload['echo']['status'] == 'succeeded'
    assert result.output_payload['echo']['output_summary'] == 'echo summary'
    assert result.output_payload['llm']['provider'] == 'fake-provider'
    assert result.output_payload['llm']['model'] == 'fake-model'
    assert 'raw echo output' not in str(result.output_payload)
    assert 'Authorization: Bearer token' not in str(result.output_payload)

    graph_span = next(span for span in sink.spans.values() if span.span_type == 'graph')
    echo_node_span = next(span for span in sink.spans.values() if span.span_type == 'node' and span.name == 'echo')
    llm_node_span = next(span for span in sink.spans.values() if span.span_type == 'node' and span.name == 'llm_summary')
    tool_span = next(span for span in sink.spans.values() if span.span_type == 'tool')
    llm_span = next(span for span in sink.spans.values() if span.span_type == 'llm')

    assert graph_span.status == 'succeeded'
    assert echo_node_span.status == 'succeeded'
    assert llm_node_span.status == 'succeeded'
    assert tool_span.status == 'succeeded'
    assert llm_span.status == 'succeeded'
    assert 'secret.txt' not in str(tool_span.started_metadata)
    assert 'secret.txt' not in str(llm_span.started_metadata)
    assert 'provider_response' not in str(llm_span.metadata)
    assert llm_span.metadata['provider'] == 'fake-provider'
    assert llm_span.metadata['model'] == 'fake-model'


def test_minimal_llm_workflow_continues_when_echo_is_policy_denied() -> None:
    sink = RecordingEventSink()
    inner_llm_client = RecordingLLMClient(result=LLMResult(content='final summary', provider='fake-provider', model='fake-model', input_tokens=1, output_tokens=1, raw={'provider_response': 'hidden'}))
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
        event_sink=sink,
        llm_client=ObservedLLMClient(inner=inner_llm_client, event_sink=sink, observability=ObservabilityContext(run_id=2, thread_id='thread-2')),
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

    result = LangGraphRunner().run_graph_once(run_id=2, runtime=runtime, input_payload={'prompt': 'summarize this'})

    assert result.status == 'succeeded'
    assert result.output_payload['echo']['status'] == 'denied'
    assert result.output_payload['summary'] == 'final summary'
    tool_span = next(span for span in sink.spans.values() if span.span_type == 'tool')
    assert tool_span.status == 'failed'
