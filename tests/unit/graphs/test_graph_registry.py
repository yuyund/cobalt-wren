"""Tests for the graph registry mechanism and built-in catalog."""

from __future__ import annotations

import pytest

from langgraph_automation.graphs.constants import DEFAULT_GRAPH_KIND
from langgraph_automation.graphs.registry import (
    GraphRegistry,
    UnknownGraphKindError,
    build_graph_registry,
    default_graph_kind,
)
from langgraph_automation.graphs.types import GraphDefinition, GraphRuntimeRequirements
from langgraph_automation.workflows.catalog import BUILTIN_GRAPH_DEFINITIONS, build_builtin_graph_registry


def test_built_in_catalog_registers_the_minimal_reference_workflow() -> None:
    registry = build_builtin_graph_registry()
    definition = registry.get(DEFAULT_GRAPH_KIND)

    assert default_graph_kind() == DEFAULT_GRAPH_KIND
    assert registry.supported_graph_kinds() == (DEFAULT_GRAPH_KIND,)
    assert DEFAULT_GRAPH_KIND in registry.definitions_by_kind
    assert BUILTIN_GRAPH_DEFINITIONS[0].builder.__module__.startswith('langgraph_automation.workflows.reference.llm_echo_summary')
    assert definition.kind == DEFAULT_GRAPH_KIND
    assert definition.builder.__module__.startswith('langgraph_automation.workflows.reference.llm_echo_summary')
    assert definition.requires_llm is True
    assert definition.required_tools == ('echo',)
    assert 'reference diagnostic workflow' in definition.description.lower()
    assert definition.requirements == GraphRuntimeRequirements(requires_llm=True, required_tools=('echo',))
    assert registry.graph_requirements()[DEFAULT_GRAPH_KIND] == GraphRuntimeRequirements(requires_llm=True, required_tools=('echo',))


def test_graph_registry_rejects_unknown_graph_kind() -> None:
    registry = build_graph_registry(BUILTIN_GRAPH_DEFINITIONS)
    with pytest.raises(UnknownGraphKindError, match='Unsupported graph kind'):
        registry.get('unknown-kind')


def test_graph_registry_rejects_duplicate_kinds() -> None:
    definition = BUILTIN_GRAPH_DEFINITIONS[0]
    duplicate = GraphDefinition(
        kind=definition.kind,
        builder=definition.builder,
        requires_llm=definition.requires_llm,
        required_tools=definition.required_tools,
        description=definition.description,
    )

    with pytest.raises(ValueError, match='duplicate graph kind'):
        GraphRegistry(definitions=(definition, duplicate))
