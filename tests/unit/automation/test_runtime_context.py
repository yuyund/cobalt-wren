"""Runtime context tests."""

from __future__ import annotations

import logging

from langgraph_automation.graphs.runtime import GraphRuntime
from langgraph_automation.integrations.observability.types import ObservabilityContext, SpanRef


def test_graph_runtime_with_parent_span_preserves_dependencies() -> None:
    runtime = GraphRuntime(
        logger=logging.getLogger('test-runtime'),
        observability=ObservabilityContext(run_id=1, thread_id='thread-1'),
    )

    updated = runtime.with_parent_span(SpanRef('span-1'), node_name='planner')

    assert updated is not runtime
    assert updated.observability.run_id == 1
    assert updated.observability.thread_id == 'thread-1'
    assert updated.observability.parent_span == SpanRef('span-1')
    assert updated.observability.node_name == 'planner'
    assert updated.llm_client is None
    assert updated.tool_registry is None
    assert runtime.observability.parent_span is None
