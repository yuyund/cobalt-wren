"""LangGraph runner tests."""

from __future__ import annotations

import logging

import pytest
from langgraph.graph import END, START, StateGraph

from langgraph_automation.graphs.instrumentation import wrap_observed_node
from langgraph_automation.graphs.runner import LangGraphRunner
from langgraph_automation.graphs.runtime import GraphRuntime
from langgraph_automation.workflows.reference.llm_echo_summary.state import LlmEchoSummaryState
from langgraph_automation.integrations.observability.types import ObservabilityContext
from tests.support.failing_event_sink import FailingGraphEventSink
from tests.support.recording_event_sink import RecordingEventSink


def test_run_graph_once_invokes_compiled_graph_and_emits_spans(monkeypatch: pytest.MonkeyPatch) -> None:
    sink = RecordingEventSink()
    runtime = GraphRuntime(
        logger=logging.getLogger('test.runner'),
        observability=ObservabilityContext(run_id=1, thread_id='thread-1'),
        event_sink=sink,
    )
    runner = LangGraphRunner()
    seen_state: dict[str, object] = {}

    def build_test_graph(observed_runtime: GraphRuntime):
        graph = StateGraph(LlmEchoSummaryState)

        def planner(state: LlmEchoSummaryState, _: GraphRuntime) -> LlmEchoSummaryState:
            seen_state.clear()
            seen_state.update(dict(state))
            return {
                'current_node': 'planner',
                'metadata': {'phase': state.get('metadata', {}).get('phase', 'run'), 'planned': True},
            }

        def summarizer(state: LlmEchoSummaryState, _: GraphRuntime) -> LlmEchoSummaryState:
            return {
                'current_node': 'summarizer',
                'output_payload': {'summary': 'done'},
                'metadata': dict(state.get('metadata', {})),
            }

        graph.add_node('planner', wrap_observed_node('planner', planner, observed_runtime))
        graph.add_node('summarizer', wrap_observed_node('summarizer', summarizer, observed_runtime))
        graph.add_edge(START, 'planner')
        graph.add_edge('planner', 'summarizer')
        graph.add_edge('summarizer', END)
        return graph.compile(name='test-graph')

    monkeypatch.setattr('langgraph_automation.graphs.runner.build_graph', build_test_graph)

    result = runner.run_graph_once(run_id=1, runtime=runtime, input_payload={'text': 'secret token /tmp/secret.txt'})

    assert result.status == 'succeeded'
    assert result.output_payload['summary'] == 'done'
    assert result.last_node_name == 'summarizer'
    assert result.output_payload == {'summary': 'done'}
    assert 'input_payload' not in seen_state
    assert 'input_summary' in seen_state
    assert seen_state['input_summary']['keys'] == ['text']
    assert sink.run_events[0].kind == 'run.started'
    assert sink.run_events[-1].kind == 'run.completed'
    graph_span = next(span for span in sink.spans.values() if span.span_type == 'graph')
    node_spans = [span for span in sink.spans.values() if span.span_type == 'node']
    assert graph_span.status == 'succeeded'
    assert {span.name for span in node_spans} == {'planner', 'summarizer'}


def test_run_graph_once_returns_failed_result_when_graph_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    sink = RecordingEventSink()
    runtime = GraphRuntime(
        logger=logging.getLogger('test.runner.failure'),
        observability=ObservabilityContext(run_id=2, thread_id='thread-2'),
        event_sink=sink,
    )
    runner = LangGraphRunner()

    def build_failing_graph(observed_runtime: GraphRuntime):
        graph = StateGraph(LlmEchoSummaryState)

        def boom(_: LlmEchoSummaryState, __: GraphRuntime) -> LlmEchoSummaryState:
            raise ValueError('boom')

        graph.add_node('planner', wrap_observed_node('planner', boom, observed_runtime))
        graph.add_edge(START, 'planner')
        graph.add_edge('planner', END)
        return graph.compile(name='failing-graph')

    monkeypatch.setattr('langgraph_automation.graphs.runner.build_graph', build_failing_graph)

    result = runner.run_graph_once(run_id=2, runtime=runtime, input_payload={})

    assert result.status == 'failed'
    assert result.error_message == 'boom'
    assert sink.run_events[0].kind == 'run.started'
    assert sink.run_events[-1].kind == 'run.failed'
    graph_span = next(span for span in sink.spans.values() if span.span_type == 'graph')
    node_span = next(span for span in sink.spans.values() if span.span_type == 'node')
    assert graph_span.status == 'failed'
    assert node_span.status == 'failed'


def test_run_graph_once_preserves_primary_failure_when_span_failed_fails(caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch) -> None:
    sink = FailingGraphEventSink(RuntimeError('Authorization: Bearer secret-token /tmp/leak.txt'))
    runtime = GraphRuntime(
        logger=logging.getLogger('test.runner.failure-mask'),
        observability=ObservabilityContext(run_id=3, thread_id='thread-3'),
        event_sink=sink,
    )
    runner = LangGraphRunner()

    def build_failing_graph(observed_runtime: GraphRuntime):
        graph = StateGraph(LlmEchoSummaryState)

        def boom(_: LlmEchoSummaryState, __: GraphRuntime) -> LlmEchoSummaryState:
            raise ValueError('primary graph failure')

        graph.add_node('planner', wrap_observed_node('planner', boom, observed_runtime))
        graph.add_edge(START, 'planner')
        graph.add_edge('planner', END)
        return graph.compile(name='failing-graph-mask')

    monkeypatch.setattr('langgraph_automation.graphs.runner.build_graph', build_failing_graph)

    caplog.set_level(logging.WARNING)
    result = runner.run_graph_once(run_id=3, runtime=runtime, input_payload={})

    assert result.status == 'failed'
    assert result.error_message == 'primary graph failure'
    assert 'Observability failure suppressed' in caplog.text
    assert 'secret-token' not in caplog.text
    assert '/tmp/leak.txt' not in caplog.text


def test_resume_graph_once_is_unsupported() -> None:
    runtime = GraphRuntime(logger=logging.getLogger('test.runner.resume'))
    runner = LangGraphRunner()

    with pytest.raises(NotImplementedError, match='checkpoint resume'):
        runner.resume_graph_once(run_id=3, runtime=runtime, input_payload={})
