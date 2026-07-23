"""Observability context rebinding tests."""

from __future__ import annotations

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


def test_updated_context_rebinds_multiple_supported_dependencies() -> None:
    dependencies = [
        ObservabilityBoundDouble(label="llm"),
        ObservabilityBoundDouble(label="tools"),
        ObservabilityBoundDouble(label="artifacts"),
        ObservabilityBoundDouble(label="checkpoints"),
    ]
    base = ObservabilityContext(run_id=7, thread_id="thread-7")
    updated = base.with_parent_span(SpanRef("span-1"), node_name="planner")

    rebound = [bind_observability_context(item, updated) for item in dependencies]

    assert all(item.bound_context == updated for item in rebound)
    assert all(original.bound_context is None for original in dependencies)
    assert base.parent_span is None
    assert base.node_name == ""
