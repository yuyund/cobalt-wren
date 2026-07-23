"""Built-in workflow catalog composition."""

from __future__ import annotations

from langgraph_automation.api.plugins import Plugin, PluginContributions, PluginMetadata
from langgraph_automation.api.workflow import WorkflowContribution
from langgraph_automation.plugins.registry import PluginRegistry
from langgraph_automation.workflows.reference.llm_echo_summary.definition import (
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

def get_builtin_workflow_plugins() -> tuple[Plugin, ...]:
    return _BUILTIN_WORKFLOW_PLUGINS


def create_builtin_workflow_registry() -> PluginRegistry:
    registry = PluginRegistry()
    register_builtin_workflows(registry)
    return registry


def register_builtin_workflows(registry: PluginRegistry) -> None:
    for plugin in get_builtin_workflow_plugins():
        registry.register(plugin)
