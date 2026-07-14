"""Tests for built-in workflow catalog composition."""

from __future__ import annotations

from langgraph_automation.graphs.constants import DEFAULT_GRAPH_KIND
from langgraph_automation.workflows.catalog import BUILTIN_GRAPH_DEFINITIONS, build_builtin_graph_registry


def test_builtin_workflow_catalog_contains_the_reference_diagnostic_workflow() -> None:
    registry = build_builtin_graph_registry()

    assert len(BUILTIN_GRAPH_DEFINITIONS) == 1
    assert registry.supported_graph_kinds() == (DEFAULT_GRAPH_KIND,)
    assert registry.get(DEFAULT_GRAPH_KIND).description.startswith('Reference diagnostic workflow')
