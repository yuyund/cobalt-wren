"""Built-in workflow catalog composition.

The foundation currently ships no product workflows. Authoring examples live
under ``examples/`` and are never registered implicitly.
"""

from __future__ import annotations

from cobalt_wren.api.plugins import Plugin
from cobalt_wren.plugins.registry import PluginRegistry

_BUILTIN_WORKFLOW_PLUGINS: tuple[Plugin, ...] = ()


def get_builtin_workflow_plugins() -> tuple[Plugin, ...]:
    return _BUILTIN_WORKFLOW_PLUGINS


def create_builtin_workflow_registry() -> PluginRegistry:
    registry = PluginRegistry()
    register_builtin_workflows(registry)
    return registry


def register_builtin_workflows(registry: PluginRegistry) -> None:
    for plugin in get_builtin_workflow_plugins():
        registry.register(plugin)
