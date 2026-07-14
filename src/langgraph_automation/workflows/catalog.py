"""Built-in workflow catalog composition.

Concrete workflow definitions live under ``workflows/reference`` and future
application workflows should be composed here without teaching the execution
foundation about their implementation details.
"""

from __future__ import annotations

from langgraph_automation.graphs.registry import GraphRegistry, build_graph_registry
from langgraph_automation.workflows.reference.llm_echo_summary.definition import (
    LLM_ECHO_SUMMARY_GRAPH_DEFINITION,
)

BUILTIN_GRAPH_DEFINITIONS = (
    LLM_ECHO_SUMMARY_GRAPH_DEFINITION,
)


def build_builtin_graph_registry() -> GraphRegistry:
    return build_graph_registry(BUILTIN_GRAPH_DEFINITIONS)
