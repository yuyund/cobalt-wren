"""Observability context rebinding tests."""

from __future__ import annotations

import logging

from langgraph_automation.graphs.runtime import GraphRuntime
from langgraph_automation.integrations.observability.context import bind_observability_context
from langgraph_automation.integrations.observability.types import ObservabilityContext, SpanRef
from tests.support.observability_doubles import ObservabilityBoundDouble


def test_bind_observability_context_rebinds_supported_objects() -> None:
    context = ObservabilityContext(run_id=1, thread_id='thread-1')
    obj = ObservabilityBoundDouble(label='demo')

    rebound = bind_observability_context(obj, context)

    assert rebound is not obj
    assert rebound.bound_context == context


def test_bind_observability_context_leaves_unsupported_objects_and_none_as_is() -> None:
    context = ObservabilityContext(run_id=1, thread_id='thread-1')
    sentinel = object()

    assert bind_observability_context(None, context) is None
    assert bind_observability_context(sentinel, context) is sentinel


def test_graph_runtime_with_parent_span_rebinds_optional_dependencies() -> None:
    llm = ObservabilityBoundDouble(label='llm')
    tools = ObservabilityBoundDouble(label='tools')
    artifacts = ObservabilityBoundDouble(label='artifacts')
    checkpoints = ObservabilityBoundDouble(label='checkpoints')
    runtime = GraphRuntime(
        logger=logging.getLogger('test-runtime-bind'),
        observability=ObservabilityContext(run_id=7, thread_id='thread-7'),
        llm_client=llm,
        tool_registry=tools,
        artifact_store=artifacts,
        checkpoint_store=checkpoints,
    )

    updated = runtime.with_parent_span(SpanRef('span-1'), node_name='planner')

    assert updated is not runtime
    assert updated.observability.parent_span == SpanRef('span-1')
    assert updated.observability.node_name == 'planner'
    assert updated.llm_client.bound_context == updated.observability
    assert updated.tool_registry.bound_context == updated.observability
    assert updated.artifact_store.bound_context == updated.observability
    assert updated.checkpoint_store.bound_context == updated.observability
    assert runtime.observability.parent_span is None
    assert runtime.observability.node_name == ''
    assert runtime.llm_client.bound_context is None
