"""Registry definition for the llm_echo_summary reference diagnostic workflow."""

from __future__ import annotations

from langgraph_automation.graphs.constants import LLM_ECHO_SUMMARY_GRAPH_KIND
from langgraph_automation.graphs.types import GraphDefinition

from .graph import build_llm_echo_summary_graph

LLM_ECHO_SUMMARY_GRAPH_DEFINITION = GraphDefinition(
    kind=LLM_ECHO_SUMMARY_GRAPH_KIND,
    builder=build_llm_echo_summary_graph,
    requires_llm=True,
    required_tools=('echo',),
    description=(
        'Reference diagnostic workflow that verifies LLM, EchoTool, '
        'observability, and safe output wiring through GraphRuntime.'
    ),
)
