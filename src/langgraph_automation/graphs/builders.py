"""LangGraph compiled graph construction."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from langgraph_automation.apps.automation.services.workflow_config import MINIMAL_GRAPH_KIND
from langgraph_automation.graphs.instrumentation import wrap_observed_node
from langgraph_automation.graphs.nodes.minimal import echo_tool_node, llm_summary_node
from langgraph_automation.graphs.runtime import GraphRuntime
from langgraph_automation.graphs.states import AutomationState

SUPPORTED_GRAPH_KINDS = frozenset({MINIMAL_GRAPH_KIND})


def build_graph(runtime: GraphRuntime):
    """Build and compile the minimal production graph."""

    graph_kind = runtime.workflow_config.graph.kind or MINIMAL_GRAPH_KIND
    if graph_kind not in SUPPORTED_GRAPH_KINDS:
        raise ValueError(f'Unsupported graph kind: {graph_kind}')

    graph = StateGraph(AutomationState)
    graph.add_node('echo', wrap_observed_node('echo', echo_tool_node, runtime))
    graph.add_node('llm_summary', wrap_observed_node('llm_summary', llm_summary_node, runtime))
    graph.add_edge(START, 'echo')
    graph.add_edge('echo', 'llm_summary')
    graph.add_edge('llm_summary', END)
    return graph.compile(name=graph_kind)
