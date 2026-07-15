"""Internal manual plugin registry MVP."""

from __future__ import annotations

from collections.abc import Iterable

from langgraph_automation.api.errors import PluginRegistrationError, PluginResolutionError
from langgraph_automation.api.plugins import (
    EventSinkContribution,
    Plugin,
    ProviderContribution,
    StoreContribution,
    ToolContribution,
)
from langgraph_automation.api.workflow import WorkflowContribution

_PLUGIN_REGISTRY_COMPONENT = 'plugin_registry'


class PluginRegistry:
    def __init__(self, plugins: Iterable[Plugin] | None = None) -> None:
        self._plugins: dict[str, Plugin] = {}
        self._workflows: dict[str, WorkflowContribution] = {}
        self._tools: dict[str, ToolContribution] = {}
        self._providers: dict[str, ProviderContribution] = {}
        self._stores: dict[tuple[str, str], StoreContribution] = {}
        self._event_sinks: dict[str, EventSinkContribution] = {}

        if plugins is not None:
            for plugin in plugins:
                self.register(plugin)

    def register(self, plugin: Plugin) -> None:
        plugin_name = plugin.metadata.name
        if plugin_name in self._plugins:
            raise self._duplicate_plugin_error(plugin_name)

        seen_tools: set[str] = set()
        seen_workflows: set[str] = set()
        seen_providers: set[str] = set()
        seen_stores: set[tuple[str, str]] = set()
        seen_event_sinks: set[str] = set()

        for workflow in plugin.contributions.workflows:
            if workflow.kind in seen_workflows or workflow.kind in self._workflows:
                raise self._duplicate_contribution_error(
                    contribution_scope='workflows',
                    contribution_name=workflow.kind,
                    metadata={
                        'plugin_name': plugin_name,
                        'contribution_scope': 'workflows',
                        'contribution_name': workflow.kind,
                    },
                )
            seen_workflows.add(workflow.kind)

        for tool in plugin.contributions.tools:
            if tool.name in seen_tools or tool.name in self._tools:
                raise self._duplicate_contribution_error(
                    contribution_scope='tools',
                    contribution_name=tool.name,
                    metadata={
                        'plugin_name': plugin_name,
                        'contribution_scope': 'tools',
                        'contribution_name': tool.name,
                    },
                )
            seen_tools.add(tool.name)

        for provider in plugin.contributions.providers:
            if provider.name in seen_providers or provider.name in self._providers:
                raise self._duplicate_contribution_error(
                    contribution_scope='providers',
                    contribution_name=provider.name,
                    metadata={
                        'plugin_name': plugin_name,
                        'contribution_scope': 'providers',
                        'contribution_name': provider.name,
                    },
                )
            seen_providers.add(provider.name)

        for store in plugin.contributions.stores:
            store_key = (store.store_type, store.backend_name)
            if store_key in seen_stores or store_key in self._stores:
                raise self._duplicate_store_error(plugin_name, store)
            seen_stores.add(store_key)

        for event_sink in plugin.contributions.event_sinks:
            if event_sink.backend_name in seen_event_sinks or event_sink.backend_name in self._event_sinks:
                raise self._duplicate_contribution_error(
                    contribution_scope='event_sinks',
                    contribution_name=event_sink.backend_name,
                    metadata={
                        'plugin_name': plugin_name,
                        'contribution_scope': 'event_sinks',
                        'contribution_name': event_sink.backend_name,
                    },
                )
            seen_event_sinks.add(event_sink.backend_name)

        self._plugins[plugin_name] = plugin
        for workflow in plugin.contributions.workflows:
            self._workflows[workflow.kind] = workflow
        for tool in plugin.contributions.tools:
            self._tools[tool.name] = tool
        for provider in plugin.contributions.providers:
            self._providers[provider.name] = provider
        for store in plugin.contributions.stores:
            self._stores[(store.store_type, store.backend_name)] = store
        for event_sink in plugin.contributions.event_sinks:
            self._event_sinks[event_sink.backend_name] = event_sink

    def get_plugin(self, name: str) -> Plugin:
        try:
            return self._plugins[name]
        except KeyError as exc:
            raise self._unknown_plugin_error(name) from exc

    def get_tool(self, name: str) -> ToolContribution:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise self._unknown_tool_error(name) from exc

    def get_workflow(self, kind: str) -> WorkflowContribution:
        try:
            return self._workflows[kind]
        except KeyError as exc:
            raise self._unknown_workflow_error(kind) from exc

    def get_provider(self, name: str) -> ProviderContribution:
        try:
            return self._providers[name]
        except KeyError as exc:
            raise self._unknown_provider_error(name) from exc

    def get_store(self, store_type: str, backend_name: str) -> StoreContribution:
        key = (store_type, backend_name)
        try:
            return self._stores[key]
        except KeyError as exc:
            raise self._unknown_store_error(store_type, backend_name) from exc

    def get_event_sink(self, backend_name: str) -> EventSinkContribution:
        try:
            return self._event_sinks[backend_name]
        except KeyError as exc:
            raise self._unknown_event_sink_error(backend_name) from exc

    def list_plugins(self) -> tuple[Plugin, ...]:
        return tuple(self._plugins.values())

    @staticmethod
    def _duplicate_plugin_error(plugin_name: str) -> PluginRegistrationError:
        return PluginRegistrationError(
            f"Plugin registration failed: duplicate plugin name '{plugin_name}'.",
            code='PLUGIN_DUPLICATE_NAME',
            component=_PLUGIN_REGISTRY_COMPONENT,
            metadata={'plugin_name': plugin_name},
        )

    @staticmethod
    def _duplicate_contribution_error(*, contribution_scope: str, contribution_name: str, metadata: dict[str, str]) -> PluginRegistrationError:
        return PluginRegistrationError(
            f"Plugin registration failed: duplicate {contribution_scope[:-1]} contribution '{contribution_name}'.",
            code='PLUGIN_CONTRIBUTION_CONFLICT',
            component=_PLUGIN_REGISTRY_COMPONENT,
            metadata=metadata,
        )

    @staticmethod
    def _duplicate_store_error(plugin_name: str, store: StoreContribution) -> PluginRegistrationError:
        return PluginRegistrationError(
            f"Plugin registration failed: duplicate store backend '{store.store_type}:{store.backend_name}'.",
            code='PLUGIN_CONTRIBUTION_CONFLICT',
            component=_PLUGIN_REGISTRY_COMPONENT,
            metadata={
                'plugin_name': plugin_name,
                'contribution_scope': 'stores',
                'store_type': store.store_type,
                'backend_name': store.backend_name,
            },
        )

    @staticmethod
    def _unknown_plugin_error(name: str) -> PluginResolutionError:
        return PluginResolutionError(
            f"Plugin resolution failed: plugin '{name}' is not registered.",
            code='PLUGIN_UNKNOWN',
            component=_PLUGIN_REGISTRY_COMPONENT,
            metadata={'plugin_name': name},
        )

    @staticmethod
    def _unknown_tool_error(name: str) -> PluginResolutionError:
        return PluginResolutionError(
            f"Plugin resolution failed: tool '{name}' is not registered.",
            code='PLUGIN_UNKNOWN_TOOL',
            component=_PLUGIN_REGISTRY_COMPONENT,
            metadata={'tool_name': name},
        )

    @staticmethod
    def _unknown_workflow_error(kind: str) -> PluginResolutionError:
        return PluginResolutionError(
            f"Plugin resolution failed: workflow kind '{kind}' is not registered.",
            code='PLUGIN_UNKNOWN_WORKFLOW',
            component=_PLUGIN_REGISTRY_COMPONENT,
            metadata={'workflow_kind': kind},
        )

    @staticmethod
    def _unknown_provider_error(name: str) -> PluginResolutionError:
        return PluginResolutionError(
            f"Plugin resolution failed: provider '{name}' is not registered.",
            code='PLUGIN_UNKNOWN_PROVIDER',
            component=_PLUGIN_REGISTRY_COMPONENT,
            metadata={'provider_name': name},
        )

    @staticmethod
    def _unknown_store_error(store_type: str, backend_name: str) -> PluginResolutionError:
        return PluginResolutionError(
            f"Plugin resolution failed: store '{store_type}:{backend_name}' is not registered.",
            code='PLUGIN_UNKNOWN_STORE',
            component=_PLUGIN_REGISTRY_COMPONENT,
            metadata={'store_type': store_type, 'backend_name': backend_name},
        )

    @staticmethod
    def _unknown_event_sink_error(backend_name: str) -> PluginResolutionError:
        return PluginResolutionError(
            f"Plugin resolution failed: event sink '{backend_name}' is not registered.",
            code='PLUGIN_UNKNOWN_EVENT_SINK',
            component=_PLUGIN_REGISTRY_COMPONENT,
            metadata={'backend_name': backend_name},
        )
