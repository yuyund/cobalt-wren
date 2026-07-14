"""LangGraph compiled graph construction."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from langgraph_automation.graphs.instrumentation import wrap_observed_node
from langgraph_automation.graphs.nodes.planner import planner_node
from langgraph_automation.graphs.nodes.summarizer import summarizer_node
from langgraph_automation.graphs.runtime import GraphRuntime
from langgraph_automation.graphs.states import AutomationState


def build_graph(runtime: GraphRuntime):
    """Build and compile the minimal production graph."""

    graph = StateGraph(AutomationState)
    graph.add_node("planner", wrap_observed_node("planner", planner_node, runtime))
    graph.add_node("summarizer", wrap_observed_node("summarizer", summarizer_node, runtime))
    graph.add_edge(START, "planner")
    graph.add_edge("planner", "summarizer")
    graph.add_edge("summarizer", END)
    return graph.compile(name="langgraph-automation")
