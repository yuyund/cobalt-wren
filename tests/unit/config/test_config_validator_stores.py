"""Config validator store resolution tests."""

from __future__ import annotations

import pytest

from cobalt_wren.api.errors import PluginResolutionError, PluginValidationError
from cobalt_wren.api.plugins import Plugin, PluginContributions, PluginMetadata, StoreContribution
from cobalt_wren.config.models import NormalizedPackageConfig, RawPackageConfig
from cobalt_wren.config.normalizer import normalize_package_config
from cobalt_wren.config.validator import ConfigValidator
from cobalt_wren.plugins.registry import PluginRegistry


def _store_plugin(*, validate_config=None, create_store=None) -> Plugin:
    return Plugin(
        metadata=PluginMetadata(name="store-plugin", version="0.1.0", plugin_types=("store",)),
        contributions=PluginContributions(
            stores=(
                StoreContribution(
                    backend_name="memory",
                    store_type="vector",
                    validate_config=validate_config,
                    create_store=create_store,
                ),
                StoreContribution(
                    backend_name="memory",
                    store_type="checkpoint",
                    validate_config=validate_config,
                    create_store=create_store,
                ),
            ),
        ),
    )


def _normalized_config(*, enabled_plugins: tuple[str, ...], vector_backend: str = "memory") -> NormalizedPackageConfig:
    raw = RawPackageConfig(
        version=1,
        plugins={"enabled": enabled_plugins},
        providers={},
        tools={"allowlist": ()},
        stores={
            "vector": {"backend": vector_backend, "config": {"path": "var/vectors.sqlite"}},
        },
        event_sinks={},
        safety={"redaction_enabled": True, "safe_errors": True},
    )
    return normalize_package_config(raw)


def test_enabled_store_backend_passes_and_invokes_hook() -> None:
    calls: list[tuple[object, object]] = []

    def validate_config(*, config: object, context: object) -> None:
        calls.append((config, context))

    registry = PluginRegistry([_store_plugin(validate_config=validate_config, create_store=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("create_store should not be called")))])
    validator = ConfigValidator(registry)
    config = _normalized_config(enabled_plugins=("store-plugin",))

    validated = validator.validate(config)

    assert validated.normalized is config
    assert len(calls) == 1
    assert calls[0][0].backend == "memory"


def test_same_backend_different_store_types_are_supported() -> None:
    registry = PluginRegistry([_store_plugin()])
    validator = ConfigValidator(registry)
    config = _normalized_config(enabled_plugins=("store-plugin",))

    validated = validator.validate(config)

    assert set(validated.effective_plugins.stores) == {("vector", "memory"), ("checkpoint", "memory")}


def test_unknown_store_backend_fails() -> None:
    registry = PluginRegistry([_store_plugin()])
    validator = ConfigValidator(registry)
    config = _normalized_config(enabled_plugins=("store-plugin",), vector_backend="sqlite")

    with pytest.raises(PluginResolutionError) as excinfo:
        validator.validate(config)

    assert excinfo.value.code == "PLUGIN_UNKNOWN_STORE"
    assert excinfo.value.metadata == {"store_type": "vector", "backend": "sqlite"}


def test_empty_store_mapping_is_allowed() -> None:
    registry = PluginRegistry([_store_plugin()])
    validator = ConfigValidator(registry)
    raw = RawPackageConfig(
        version=1,
        plugins={"enabled": ("store-plugin",)},
        providers={},
        tools={"allowlist": ()},
        stores={},
        event_sinks={},
        safety={"redaction_enabled": True, "safe_errors": True},
    )
    config = normalize_package_config(raw)

    validated = validator.validate(config)

    assert validated.effective_plugins.plugin_names == ("store-plugin",)


def test_store_validation_hook_arbitrary_exception_is_wrapped() -> None:
    def validate_config(*, config: object, context: object) -> None:
        raise ValueError("boom")

    registry = PluginRegistry([_store_plugin(validate_config=validate_config)])
    validator = ConfigValidator(registry)
    config = _normalized_config(enabled_plugins=("store-plugin",))

    with pytest.raises(PluginValidationError) as excinfo:
        validator.validate(config)

    assert excinfo.value.code == "PLUGIN_VALIDATION_FAILED"
    assert isinstance(excinfo.value.__cause__, ValueError)


def test_store_validation_does_not_call_factory_hook() -> None:
    def create_store(*args, **kwargs):
        raise AssertionError("create_store should not be called")

    registry = PluginRegistry([_store_plugin(validate_config=lambda **kwargs: None, create_store=create_store)])
    validator = ConfigValidator(registry)
    config = _normalized_config(enabled_plugins=("store-plugin",))

    validator.validate(config)
