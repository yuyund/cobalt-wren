"""Config validator provider resolution tests."""

from __future__ import annotations

import pytest

from cobalt_wren.api.errors import PluginResolutionError, PluginValidationError
from cobalt_wren.api.plugins import Plugin, PluginContributions, PluginMetadata, ProviderContribution
from cobalt_wren.config.models import NormalizedPackageConfig, ProviderProfileConfig, RawPackageConfig
from cobalt_wren.config.normalizer import normalize_package_config
from cobalt_wren.config.validator import ConfigValidator
from cobalt_wren.plugins.registry import PluginRegistry


def _provider_plugin(*, validate_profile=None, create_client=None) -> Plugin:
    return Plugin(
        metadata=PluginMetadata(name="provider-plugin", version="0.1.0", plugin_types=("provider",)),
        contributions=PluginContributions(
            providers=(
                ProviderContribution(
                    name="litellm",
                    provider_type="llm",
                    validate_profile=validate_profile,
                    create_client=create_client,
                ),
            ),
        ),
    )


def _normalized_config(*, enabled_plugins: tuple[str, ...], provider_name: str = "litellm") -> NormalizedPackageConfig:
    raw = RawPackageConfig(
        version=1,
        plugins={"enabled": enabled_plugins},
        providers={"default": {"provider": provider_name, "model": "gpt-4.1-mini"}},
        tools={"allowlist": ()},
        stores={},
        event_sinks={},
        safety={"redaction_enabled": True, "safe_errors": True},
    )
    return normalize_package_config(raw)


def test_registered_and_enabled_provider_passes_and_invokes_hook() -> None:
    calls: list[tuple[ProviderProfileConfig, object]] = []

    def validate_profile(*, config: ProviderProfileConfig, context: object) -> None:
        calls.append((config, context))

    registry = PluginRegistry([_provider_plugin(validate_profile=validate_profile, create_client=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("create_client should not be called")))])
    validator = ConfigValidator(registry)
    config = _normalized_config(enabled_plugins=("provider-plugin",))

    validated = validator.validate(config)

    assert validated.normalized is config
    assert len(calls) == 1
    assert calls[0][0] == ProviderProfileConfig(provider="litellm", model="gpt-4.1-mini")


def test_registered_but_disabled_provider_fails() -> None:
    registry = PluginRegistry([_provider_plugin()])
    validator = ConfigValidator(registry)
    config = _normalized_config(enabled_plugins=())

    with pytest.raises(PluginResolutionError) as excinfo:
        validator.validate(config)

    assert excinfo.value.code == "PLUGIN_UNKNOWN_PROVIDER"
    assert excinfo.value.component == "config_validator"
    assert excinfo.value.metadata == {"provider": "litellm", "profile": "default"}


def test_unknown_provider_fails() -> None:
    registry = PluginRegistry([_provider_plugin()])
    validator = ConfigValidator(registry)
    config = _normalized_config(enabled_plugins=("provider-plugin",), provider_name="openai")

    with pytest.raises(PluginResolutionError) as excinfo:
        validator.validate(config)

    assert excinfo.value.code == "PLUGIN_UNKNOWN_PROVIDER"
    assert excinfo.value.metadata == {"provider": "openai", "profile": "default"}


def test_empty_provider_mapping_is_allowed() -> None:
    registry = PluginRegistry([_provider_plugin()])
    validator = ConfigValidator(registry)
    raw = RawPackageConfig(
        version=1,
        plugins={"enabled": ("provider-plugin",)},
        providers={},
        tools={"allowlist": ()},
        stores={},
        event_sinks={},
        safety={"redaction_enabled": True, "safe_errors": True},
    )
    config = normalize_package_config(raw)

    validated = validator.validate(config)

    assert validated.effective_plugins.plugin_names == ("provider-plugin",)


def test_provider_validation_hook_arbitrary_exception_is_wrapped() -> None:
    def validate_profile(*, config: ProviderProfileConfig, context: object) -> None:
        raise ValueError("boom")

    registry = PluginRegistry([_provider_plugin(validate_profile=validate_profile)])
    validator = ConfigValidator(registry)
    config = _normalized_config(enabled_plugins=("provider-plugin",))

    with pytest.raises(PluginValidationError) as excinfo:
        validator.validate(config)

    assert excinfo.value.code == "PLUGIN_VALIDATION_FAILED"
    assert excinfo.value.component == "config_validator"
    assert excinfo.value.__cause__ is not None
    assert isinstance(excinfo.value.__cause__, ValueError)


def test_provider_validation_hook_raised_plugin_validation_error_is_preserved() -> None:
    def validate_profile(*, config: ProviderProfileConfig, context: object) -> None:
        raise PluginValidationError("Provider validation failed.", code="PLUGIN_VALIDATION_FAILED", component="plugin_hook")

    registry = PluginRegistry([_provider_plugin(validate_profile=validate_profile)])
    validator = ConfigValidator(registry)
    config = _normalized_config(enabled_plugins=("provider-plugin",))

    with pytest.raises(PluginValidationError) as excinfo:
        validator.validate(config)

    assert excinfo.value.component == "plugin_hook"
    assert excinfo.value.code == "PLUGIN_VALIDATION_FAILED"


def test_provider_validation_does_not_call_factory_hook() -> None:
    def create_client(*args, **kwargs):
        raise AssertionError("create_client should not be called")

    registry = PluginRegistry([_provider_plugin(validate_profile=lambda **kwargs: None, create_client=create_client)])
    validator = ConfigValidator(registry)
    config = _normalized_config(enabled_plugins=("provider-plugin",))

    validator.validate(config)
