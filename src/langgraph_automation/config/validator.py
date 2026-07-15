"""Validate normalized package config against the plugin registry."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from langgraph_automation.api.errors import ConfigError, PluginResolutionError, PluginValidationError
from langgraph_automation.api.plugins import (
    EventSinkContribution,
    Plugin,
    ProviderContribution,
    StoreContribution,
    ToolContribution,
)
from langgraph_automation.config.models import (
    EffectivePluginSet,
    EventSinkBackendConfig,
    NormalizedPackageConfig,
    PluginsConfig,
    ProviderProfileConfig,
    StoreBackendConfig,
    ToolsConfig,
    ValidatedPackageConfig,
)
from langgraph_automation.plugins.registry import PluginRegistry

_CONFIG_COMPONENT = "config_validator"


@dataclass(frozen=True, slots=True)
class _ValidationContext:
    environment: str
    enabled_plugins: tuple[str, ...]
    component: str = _CONFIG_COMPONENT


class ConfigValidator:
    def __init__(self, registry: PluginRegistry) -> None:
        self._registry = registry

    def validate(self, config: NormalizedPackageConfig) -> ValidatedPackageConfig:
        if not isinstance(config, NormalizedPackageConfig):
            raise TypeError("config must be a NormalizedPackageConfig")

        context = _ValidationContext(environment=config.environment, enabled_plugins=config.plugins.enabled)
        effective_plugins = self._build_effective_plugin_set(config.plugins, context)

        self._validate_tools(config.tools, effective_plugins, context)
        self._validate_providers(config.providers, effective_plugins, context)
        self._validate_stores(config.stores, effective_plugins, context)
        self._validate_event_sinks(config.event_sinks, effective_plugins, context)

        return ValidatedPackageConfig(normalized=config, effective_plugins=effective_plugins)

    def _build_effective_plugin_set(self, plugins: PluginsConfig, context: _ValidationContext) -> EffectivePluginSet:
        enabled_plugins: list[Plugin] = []
        tool_index: dict[str, ToolContribution] = {}
        provider_index: dict[str, ProviderContribution] = {}
        store_index: dict[tuple[str, str], StoreContribution] = {}
        event_sink_index: dict[str, EventSinkContribution] = {}

        for plugin_name in plugins.enabled:
            plugin = self._get_registered_plugin(plugin_name, context)
            enabled_plugins.append(plugin)
            for tool in plugin.contributions.tools:
                tool_index[tool.name] = tool
            for provider in plugin.contributions.providers:
                provider_index[provider.name] = provider
            for store in plugin.contributions.stores:
                store_index[(store.store_type, store.backend_name)] = store
            for event_sink in plugin.contributions.event_sinks:
                event_sink_index[event_sink.backend_name] = event_sink

        return EffectivePluginSet(
            plugins=tuple(enabled_plugins),
            plugin_names=tuple(plugin.metadata.name for plugin in enabled_plugins),
            tools=tool_index,
            providers=provider_index,
            stores=store_index,
            event_sinks=event_sink_index,
        )

    def _validate_providers(
        self,
        providers: Mapping[str, ProviderProfileConfig],
        effective_plugins: EffectivePluginSet,
        context: _ValidationContext,
    ) -> None:
        for profile_name, profile in providers.items():
            provider_name = profile.provider
            contribution = effective_plugins.providers.get(provider_name)
            if contribution is None:
                raise self._plugin_resolution_error(
                    f"Plugin resolution failed: provider '{provider_name}' is not enabled.",
                    code="PLUGIN_UNKNOWN_PROVIDER",
                    metadata={"provider": provider_name, "profile": profile_name},
                )
            self._call_validate_profile(contribution, profile, context, profile_name, provider_name)

    def _validate_tools(
        self,
        tools: ToolsConfig,
        effective_plugins: EffectivePluginSet,
        context: _ValidationContext,
    ) -> None:
        allowlist = tools.allowlist
        configs = tools.configs
        for tool_name in configs:
            if tool_name not in allowlist:
                raise self._config_error(
                    "Configuration is invalid: tool config is defined for a tool not in allowlist.",
                    code="CONFIG_TOOL_CONFIG_NOT_ALLOWED",
                    metadata={"tool_name": tool_name},
                )

        for tool_name in allowlist:
            contribution = effective_plugins.tools.get(tool_name)
            if contribution is None:
                raise self._plugin_resolution_error(
                    f"Plugin resolution failed: tool '{tool_name}' is not enabled.",
                    code="PLUGIN_UNKNOWN_TOOL",
                    metadata={"tool_name": tool_name},
                )
            tool_config = configs.get(tool_name, {})
            if tool_config is None:
                tool_config = {}
            if not isinstance(tool_config, Mapping):
                raise self._config_error(
                    "Configuration is invalid: tool config must be a mapping.",
                    code="CONFIG_INVALID_FIELD_TYPE",
                    metadata={"tool_name": tool_name},
                )
            self._call_validate_config(contribution.validate_config, tool_config, context, "tools", tool_name, "tool")

    def _validate_stores(
        self,
        stores: Mapping[str, StoreBackendConfig],
        effective_plugins: EffectivePluginSet,
        context: _ValidationContext,
    ) -> None:
        for store_type, store_config in stores.items():
            key = (store_type, store_config.backend)
            contribution = effective_plugins.stores.get(key)
            if contribution is None:
                raise self._plugin_resolution_error(
                    f"Plugin resolution failed: store backend '{store_config.backend}' for store type '{store_type}' is not enabled.",
                    code="PLUGIN_UNKNOWN_STORE",
                    metadata={"store_type": store_type, "backend": store_config.backend},
                )
            self._call_validate_config(
                contribution.validate_config,
                store_config,
                context,
                store_type,
                store_config.backend,
                "store",
            )

    def _validate_event_sinks(
        self,
        event_sinks: Mapping[str, EventSinkBackendConfig],
        effective_plugins: EffectivePluginSet,
        context: _ValidationContext,
    ) -> None:
        for sink_name, sink_config in event_sinks.items():
            contribution = effective_plugins.event_sinks.get(sink_config.backend)
            if contribution is None:
                raise self._plugin_resolution_error(
                    f"Plugin resolution failed: event sink backend '{sink_config.backend}' is not enabled.",
                    code="PLUGIN_UNKNOWN_EVENT_SINK",
                    metadata={"backend": sink_config.backend},
                )
            self._call_validate_config(
                contribution.validate_config,
                sink_config,
                context,
                sink_name,
                sink_config.backend,
                "event_sink",
            )

    def _get_registered_plugin(self, plugin_name: str, _context: _ValidationContext) -> Plugin:
        try:
            return self._registry.get_plugin(plugin_name)
        except PluginResolutionError as exc:
            raise self._plugin_resolution_error(
                f"Plugin resolution failed: plugin '{plugin_name}' is not registered.",
                code=exc.code,
                metadata={"plugin_name": plugin_name},
            ) from exc

    def _call_validate_profile(
        self,
        contribution: ProviderContribution,
        profile: ProviderProfileConfig,
        context: _ValidationContext,
        profile_name: str,
        provider_name: str,
    ) -> None:
        hook = contribution.validate_profile
        if hook is None:
            return
        self._invoke_validation_hook(
            hook,
            config=profile,
            context=context,
            contribution_name=provider_name,
            contribution_scope="provider",
            metadata={"provider": provider_name, "profile": profile_name},
        )

    def _call_validate_config(
        self,
        hook: Any,
        config: object,
        context: _ValidationContext,
        contribution_name: str,
        backend_name: str,
        contribution_scope: str,
    ) -> None:
        if hook is None:
            return
        metadata: dict[str, object] = {"contribution_name": contribution_name}
        if contribution_scope == "tool":
            metadata["tool_name"] = contribution_name
        elif contribution_scope == "store":
            metadata["store_type"] = contribution_name
            metadata["backend"] = backend_name
        elif contribution_scope == "event_sink":
            metadata["backend"] = backend_name
        self._invoke_validation_hook(
            hook,
            config=config,
            context=context,
            contribution_name=contribution_name,
            contribution_scope=contribution_scope,
            metadata=metadata,
        )

    def _invoke_validation_hook(
        self,
        hook: Any,
        *,
        config: object,
        context: _ValidationContext,
        contribution_name: str,
        contribution_scope: str,
        metadata: dict[str, object],
    ) -> None:
        try:
            hook(config=config, context=context)
        except PluginValidationError:
            raise
        except Exception as exc:
            raise PluginValidationError(
                "Plugin validation failed.",
                code="PLUGIN_VALIDATION_FAILED",
                component=_CONFIG_COMPONENT,
                metadata={
                    **metadata,
                    "contribution_scope": contribution_scope,
                    "contribution_name": contribution_name,
                    "environment": context.environment,
                },
            ) from exc

    @staticmethod
    def _config_error(safe_message: str, *, code: str, metadata: dict[str, Any] | None = None) -> ConfigError:
        return ConfigError(safe_message, code=code, component=_CONFIG_COMPONENT, metadata=metadata)

    @staticmethod
    def _plugin_resolution_error(safe_message: str, *, code: str, metadata: dict[str, Any] | None = None) -> PluginResolutionError:
        return PluginResolutionError(safe_message, code=code, component=_CONFIG_COMPONENT, metadata=metadata)


def validate_package_config(config: NormalizedPackageConfig, *, registry: PluginRegistry) -> ValidatedPackageConfig:
    return ConfigValidator(registry).validate(config)
