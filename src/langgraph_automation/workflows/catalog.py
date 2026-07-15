"""Built-in workflow catalog composition."""

from __future__ import annotations

from langgraph_automation.api.plugins import Plugin, PluginContributions, PluginMetadata
from langgraph_automation.api.workflow import WorkflowContribution
from langgraph_automation.graphs.registry import GraphRegistry, build_graph_registry
from langgraph_automation.graphs.types import GraphDefinition
from langgraph_automation.plugins.registry import PluginRegistry
from langgraph_automation.workflows.adapter import build_workflow_graph
from langgraph_automation.workflows.reference.llm_echo_summary.definition import (
    LLM_ECHO_SUMMARY_GRAPH_DEFINITION,
    REFERENCE_WORKFLOW_KIND,
    llm_echo_summary_workflow_contribution,
)

_BUILTIN_REFERENCE_WORKFLOW_CONTRIBUTIONS: tuple[WorkflowContribution, ...] = (
    llm_echo_summary_workflow_contribution(),
)

_BUILTIN_WORKFLOW_PLUGINS: tuple[Plugin, ...] = (
    Plugin(
        metadata=PluginMetadata(
            name='langgraph_automation.reference_workflows',
            version='0.1.0',
            description='Built-in reference workflows.',
            plugin_types=('workflow',),
            provides={
                'workflows': (REFERENCE_WORKFLOW_KIND,),
            },
        ),
        contributions=PluginContributions(
            workflows=_BUILTIN_REFERENCE_WORKFLOW_CONTRIBUTIONS,
        ),
    ),
)

BUILTIN_GRAPH_DEFINITIONS: tuple[GraphDefinition, ...] = (LLM_ECHO_SUMMARY_GRAPH_DEFINITION,)


def get_builtin_workflow_plugins() -> tuple[Plugin, ...]:
    return _BUILTIN_WORKFLOW_PLUGINS


def create_builtin_workflow_registry() -> PluginRegistry:
    registry = PluginRegistry()
    register_builtin_workflows(registry)
    return registry


def register_builtin_workflows(registry: PluginRegistry) -> None:
    for plugin in get_builtin_workflow_plugins():
        registry.register(plugin)


def build_builtin_graph_registry() -> GraphRegistry:
    graph_definitions: list[GraphDefinition] = []
    for plugin in get_builtin_workflow_plugins():
        for contribution in plugin.contributions.workflows:
            graph_definition = build_workflow_graph(contribution.definition)
            if not isinstance(graph_definition, GraphDefinition):
                raise TypeError('workflow build must return a GraphDefinition')
            graph_definitions.append(graph_definition)
    return build_graph_registry(tuple(graph_definitions))
