"""LangGraph compiled graph construction."""

from __future__ import annotations

from langgraph_automation.graphs.runtime import GraphRuntime


def build_graph(runtime: GraphRuntime):
    """Build and compile the registered graph."""

    graph_definition = runtime.require_graph_registry().get(runtime.workflow_config.graph.kind)
    return graph_definition.builder(runtime)
