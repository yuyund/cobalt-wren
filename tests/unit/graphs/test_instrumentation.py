"""Instrumentation helper tests."""

from __future__ import annotations

import logging

import pytest

from langgraph_automation.graphs.instrumentation import run_observed_node
from langgraph_automation.graphs.runtime import GraphRuntime
from langgraph_automation.graphs.states import AutomationState
from langgraph_automation.integrations.observability.types import ObservabilityContext
from tests.support.recording_event_sink import RecordingEventSink


def test_run_observed_node_creates_node_span_and_returns_result() -> None:
    sink = RecordingEventSink()
    graph_span = sink.span_started(1, "graph", "graph", node_name="graph")
    runtime = GraphRuntime(
        logger=logging.getLogger("test.instrumentation"),
        observability=ObservabilityContext(run_id=1, parent_span=graph_span, node_name="graph"),
        event_sink=sink,
    )
    seen = {}

    def node_func(state: AutomationState, node_runtime: GraphRuntime) -> AutomationState:
        seen["parent_span_id"] = None if node_runtime.observability.parent_span is None else node_runtime.observability.parent_span.span_id
        seen["node_name"] = node_runtime.observability.node_name
        return {"current_node": "planner", "metadata": {"ok": True}}

    result = run_observed_node("planner", node_func, {"input_payload": {"x": 1}}, runtime)

    assert result["current_node"] == "planner"
    assert seen["node_name"] == "planner"
    assert seen["parent_span_id"] is not None
    node_span = sink.spans[seen["parent_span_id"]]
    assert node_span.name == "planner"
    assert node_span.parent_id == graph_span.span_id
    assert node_span.status == "succeeded"
    assert node_span.output_summary


def test_run_observed_node_marks_failure() -> None:
    sink = RecordingEventSink()
    graph_span = sink.span_started(1, "graph", "graph", node_name="graph")
    runtime = GraphRuntime(
        logger=logging.getLogger("test.instrumentation.failure"),
        observability=ObservabilityContext(run_id=1, parent_span=graph_span, node_name="graph"),
        event_sink=sink,
    )

    def node_func(_: AutomationState, __: GraphRuntime) -> AutomationState:
        raise ValueError("boom")

    with pytest.raises(ValueError):
        run_observed_node("planner", node_func, {"input_payload": {}}, runtime)

    node_span = next(span for span in sink.spans.values() if span.name == "planner")
    assert node_span.status == "failed"
    assert node_span.error_message == "boom"
