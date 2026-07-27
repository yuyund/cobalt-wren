"""Config validator effective plugin set tests."""

from __future__ import annotations

import pytest

from cobalt_wren.api.errors import PluginResolutionError
from cobalt_wren.api.plugins import (
    EventSinkContribution,
    Plugin,
    PluginContributions,
    PluginMetadata,
    ProviderContribution,
    StoreContribution,
    ToolContribution,
)
from cobalt_wren.config.models import (
    EffectivePluginSet,
    EventSinkBackendConfig,
    NormalizedPackageConfig,
    PluginsConfig,
    ProviderProfileConfig,
    RawPackageConfig,
    SafetyConfig,
    StoreBackendConfig,
    ToolsConfig,
    ValidatedPackageConfig,
)
from cobalt_wren.config.normalizer import normalize_package_config
from cobalt_wren.config.validator import ConfigValidator
from cobalt_wren.plugins.registry import PluginRegistry


def _build_plugin(name: str, *, include_litellm: bool = False, include_openai: bool = False, include_stdout: bool = False, include_store: bool = True) -> Plugin:
    tool = ToolContribution(name=f"{name}.search_issues")
    providers = []
    if include_litellm:
        providers.append(ProviderContribution(name="litellm", provider_type="llm"))
    if include_openai:
        providers.append(ProviderContribution(name="openai", provider_type="llm"))
    stores = [StoreContribution(backend_name="memory", store_type="vector")] if include_store else []
    event_sinks = []
    if include_stdout:
        event_sinks.append(EventSinkContribution(backend_name="stdout"))
    return Plugin(
        metadata=PluginMetadata(name=name, version="0.1.0", plugin_types=("tool", "provider", "store", "event_sink")),
        contributions=PluginContributions(
            tools=(tool,),
            providers=tuple(providers),
            stores=tuple(stores),
            event_sinks=tuple(event_sinks),
        ),
    )


def _build_normalized_config(*, enabled_plugins: tuple[str, ...]) -> NormalizedPackageConfig:
    raw = RawPackageConfig(
        version=1,
        plugins={"enabled": enabled_plugins},
        providers={
            "default": {"provider": "litellm", "model": "gpt-4.1-mini"},
        },
        tools={"allowlist": ("github.search_issues",)},
        stores={"vector": {"backend": "memory"}},
        event_sinks={"stdout": {"backend": "stdout"}},
        safety={"redaction_enabled": True, "safe_errors": True},
    )
    return normalize_package_config(raw)


def test_effective_plugin_set_is_empty_when_plugins_enabled_is_empty() -> None:
    registry = PluginRegistry([_build_plugin("github", include_litellm=True, include_stdout=True)])
    validator = ConfigValidator(registry)
    raw = RawPackageConfig(
        version=1,
        plugins={"enabled": ()},
        providers={},
        tools={"allowlist": ()},
        stores={},
        event_sinks={},
        safety={"redaction_enabled": True, "safe_errors": True},
    )
    config = normalize_package_config(raw)

    validated = validator.validate(config)

    assert isinstance(validated, ValidatedPackageConfig)
    assert validated.normalized is config
    assert validated.effective_plugins == EffectivePluginSet(
        plugins=(),
        plugin_names=(),
        tools={},
        providers={},
        stores={},
        event_sinks={},
    )


def test_effective_plugin_set_collects_enabled_plugin_contributions_only() -> None:
    registry = PluginRegistry(
        [
            _build_plugin("github", include_litellm=True, include_stdout=True),
            _build_plugin("slack", include_openai=True, include_store=False),
        ]
    )
    validator = ConfigValidator(registry)
    config = _build_normalized_config(enabled_plugins=("github",))
    config = NormalizedPackageConfig(
        version=config.version,
        environment=config.environment,
        plugins=PluginsConfig(enabled=("github",)),
        providers={"default": ProviderProfileConfig(provider="litellm", model="gpt-4.1-mini")},
        tools=ToolsConfig(allowlist=("github.search_issues",)),
        stores={"vector": StoreBackendConfig(backend="memory")},
        event_sinks={"stdout": EventSinkBackendConfig(backend="stdout")},
        limits=config.limits,
        observability=config.observability,
        safety=SafetyConfig(),
        metadata=config.metadata,
    )

    validated = validator.validate(config)

    assert validated.effective_plugins.plugin_names == ("github",)
    assert set(validated.effective_plugins.tools) == {"github.search_issues"}
    assert set(validated.effective_plugins.providers) == {"litellm"}
    assert set(validated.effective_plugins.stores) == {("vector", "memory")}
    assert set(validated.effective_plugins.event_sinks) == {"stdout"}


def test_unknown_enabled_plugin_raises_plugin_resolution_error() -> None:
    registry = PluginRegistry([_build_plugin("github", include_litellm=True)])
    validator = ConfigValidator(registry)
    config = _build_normalized_config(enabled_plugins=("missing",))

    with pytest.raises(PluginResolutionError) as excinfo:
        validator.validate(config)

    assert excinfo.value.code == "PLUGIN_UNKNOWN"
    assert excinfo.value.component == "config_validator"
    assert excinfo.value.metadata["plugin_name"] == "missing"
