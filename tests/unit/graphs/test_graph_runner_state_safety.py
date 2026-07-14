"""Runner state safety tests for checkpointable graph state boundaries."""

from __future__ import annotations

import logging

import pytest
from langgraph.graph import END, START, StateGraph

from langgraph_automation.core.summary import summarize_mapping
from langgraph_automation.graphs.instrumentation import wrap_observed_node
from langgraph_automation.graphs.runner import LangGraphRunner
from langgraph_automation.graphs.runtime import GraphRuntime
from langgraph_automation.workflows.reference.llm_echo_summary.state import LlmEchoSummaryState
from langgraph_automation.integrations.observability.types import ObservabilityContext
from tests.support.recording_event_sink import RecordingEventSink


def test_run_graph_once_uses_safe_input_summary_in_initial_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sink = RecordingEventSink()
    runtime = GraphRuntime(
        logger=logging.getLogger('test.runner.state-safety'),
        observability=ObservabilityContext(run_id=7, thread_id='thread-7'),
        event_sink=sink,
    )
    runner = LangGraphRunner()
    seen_state: dict[str, object] = {}
    raw_input = {
        'text': 'summarize this /tmp/secret.txt Authorization: Bearer secret-token',
    }

    def build_test_graph(observed_runtime: GraphRuntime):
        graph = StateGraph(LlmEchoSummaryState)

        def inspect(state: LlmEchoSummaryState, _: GraphRuntime) -> LlmEchoSummaryState:
            seen_state.clear()
            seen_state.update(dict(state))
            return {
                'current_node': 'planner',
                'output_payload': {'summary': 'ok'},
                'metadata': dict(state.get('metadata', {})),
            }

        graph.add_node('planner', wrap_observed_node('planner', inspect, observed_runtime))
        graph.add_edge(START, 'planner')
        graph.add_edge('planner', END)
        return graph.compile(name='state-safety-graph')

    monkeypatch.setattr('langgraph_automation.graphs.runner.build_graph', build_test_graph)

    result = runner.run_graph_once(run_id=7, runtime=runtime, input_payload=raw_input)

    assert result.status == 'succeeded'
    assert 'input_payload' not in seen_state
    assert 'input_summary' in seen_state
    assert seen_state['input_summary'] == summarize_mapping(raw_input)
    assert 'secret-token' not in str(seen_state['input_summary'])
    assert '/tmp/secret.txt' not in str(seen_state['input_summary'])
    assert result.output_payload == {'summary': 'ok'}
