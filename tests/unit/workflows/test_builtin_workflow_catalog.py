"""Tests for built-in workflow catalog wiring."""

from __future__ import annotations

from langgraph_automation.api.plugins import Plugin
from langgraph_automation.graphs.constants import DEFAULT_GRAPH_KIND
from langgraph_automation.plugins.registry import PluginRegistry
from langgraph_automation.workflows.catalog import (
    build_builtin_graph_registry,
    create_builtin_workflow_registry,
    get_builtin_workflow_plugins,
    register_builtin_workflows,
)


def test_get_builtin_workflow_plugins_returns_reference_workflow_plugin() -> None:
    plugins = get_builtin_workflow_plugins()

    assert isinstance(plugins, tuple)
    assert len(plugins) == 1

    plugin = plugins[0]
    assert isinstance(plugin, Plugin)
    assert plugin.metadata.name == 'langgraph_automation.reference_workflows'
    assert plugin.metadata.plugin_types == ('workflow',)
    assert plugin.metadata.provides['workflows'] == ('reference.llm_echo_summary',)
    assert len(plugin.contributions.workflows) == 1

    contribution = plugin.contributions.workflows[0]
    assert contribution.kind == 'reference.llm_echo_summary'
    assert contribution.definition.kind == 'reference.llm_echo_summary'


def test_register_builtin_workflows_registers_reference_workflow_plugin() -> None:
    registry = PluginRegistry()

    register_builtin_workflows(registry)

    plugin = registry.get_plugin('langgraph_automation.reference_workflows')
    assert registry.get_workflow('reference.llm_echo_summary') is plugin.contributions.workflows[0]


def test_create_builtin_workflow_registry_registers_reference_workflow_plugin() -> None:
    registry = create_builtin_workflow_registry()

    assert isinstance(registry, PluginRegistry)
    plugin = registry.get_plugin('langgraph_automation.reference_workflows')
    assert registry.get_workflow('reference.llm_echo_summary') is plugin.contributions.workflows[0]


def test_build_builtin_graph_registry_keeps_existing_graph_kind() -> None:
    registry = build_builtin_graph_registry()

    assert registry.supported_graph_kinds() == (DEFAULT_GRAPH_KIND,)
    assert registry.get(DEFAULT_GRAPH_KIND).builder.__module__.startswith(
        'langgraph_automation.workflows.reference.llm_echo_summary'
    )
