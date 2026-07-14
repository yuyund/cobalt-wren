"""Common node instrumentation helpers for LangGraph execution."""

from __future__ import annotations

from collections.abc import Callable
import json
from typing import TypeAlias

from langgraph_automation.core.summary import summarize_mapping
from langgraph_automation.graphs.runtime import GraphRuntime
from langgraph_automation.graphs.states import AutomationState
from langgraph_automation.integrations.observability import events as obs_events
from langgraph_automation.integrations.observability.failure_policy import suppress_observability_failure

NodeFunc: TypeAlias = Callable[[AutomationState, GraphRuntime], AutomationState]


def _summarize_result(result: AutomationState) -> str:
    return json.dumps(summarize_mapping(result), ensure_ascii=False, sort_keys=True, default=str)


def run_observed_node(
    node_name: str,
    node_func: NodeFunc,
    state: AutomationState,
    runtime: GraphRuntime,
) -> AutomationState:
    """Run a node while emitting span lifecycle events through the EventSink."""

    sink = runtime.event_sink
    parent_span = runtime.observability.parent_span
    node_runtime = runtime.with_parent_span(parent_span, node_name=node_name)
    if sink is None:
        return node_func(state, node_runtime)

    node_span = sink.span_started(
        runtime.observability.run_id or 0,
        span_type=obs_events.SPAN_NODE,
        name=node_name,
        node_name=node_name,
        parent=parent_span,
        metadata={'node_name': node_name},
    )
    observed_runtime = node_runtime.with_parent_span(node_span, node_name=node_name)

    try:
        result = node_func(state, observed_runtime)
    except Exception as primary_exc:
        failure_message = str(primary_exc)
        suppress_observability_failure(
            lambda: sink.span_failed(node_span, error_message=failure_message, metadata={'node_name': node_name}),
            context={'component': 'run_observed_node', 'operation': 'span_failed', 'node_name': node_name},
        )
        raise

    sink.span_completed(
        node_span,
        output_summary=_summarize_result(result),
        metrics={'ok': True},
        metadata={'node_name': node_name},
    )
    return result


def wrap_observed_node(node_name: str, node_func: NodeFunc, runtime: GraphRuntime) -> Callable[[AutomationState], AutomationState]:
    """Wrap a node for direct registration with StateGraph.add_node()."""

    def wrapped(state: AutomationState) -> AutomationState:
        return run_observed_node(node_name, node_func, state, runtime)

    return wrapped
