"""Reference diagnostic llm_echo_summary graph builder.

This workflow exists to verify runtime wiring, observability, tool policy,
and safe persistence. It is a diagnostic smoke-test graph, not an application
workflow.
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from langgraph_automation.graphs.instrumentation import wrap_observed_node
from langgraph_automation.graphs.runtime import GraphRuntime

from .nodes import echo_tool_node, llm_summary_node
from .state import LlmEchoSummaryState


def build_llm_echo_summary_graph(runtime: GraphRuntime):
    """Build and compile the reference diagnostic graph."""

    graph = StateGraph(LlmEchoSummaryState)
    graph.add_node('echo', wrap_observed_node('echo', echo_tool_node, runtime))
    graph.add_node('llm_summary', wrap_observed_node('llm_summary', llm_summary_node, runtime))
    graph.add_edge(START, 'echo')
    graph.add_edge('echo', 'llm_summary')
    graph.add_edge('llm_summary', END)
    return graph.compile(name='llm_echo_summary')
