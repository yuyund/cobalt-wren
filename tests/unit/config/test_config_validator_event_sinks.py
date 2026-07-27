"""Config validator event sink resolution tests."""

from __future__ import annotations

import pytest

from cobalt_wren.api.errors import PluginResolutionError, PluginValidationError
from cobalt_wren.api.plugins import EventSinkContribution, Plugin, PluginContributions, PluginMetadata
from cobalt_wren.config.models import NormalizedPackageConfig, RawPackageConfig
from cobalt_wren.config.normalizer import normalize_package_config
from cobalt_wren.config.validator import ConfigValidator
from cobalt_wren.plugins.registry import PluginRegistry


def _sink_plugin(*, validate_config=None, create_sink=None) -> Plugin:
    return Plugin(
        metadata=PluginMetadata(name="sink-plugin", version="0.1.0", plugin_types=("event_sink",)),
        contributions=PluginContributions(
            event_sinks=(
                EventSinkContribution(
                    backend_name="stdout",
                    validate_config=validate_config,
                    create_sink=create_sink,
                ),
            ),
        ),
    )


def _normalized_config(*, enabled_plugins: tuple[str, ...], backend: str = "stdout") -> NormalizedPackageConfig:
    raw = RawPackageConfig(
        version=1,
        plugins={"enabled": enabled_plugins},
        providers={},
        tools={"allowlist": ()},
        stores={},
        event_sinks={"stdout": {"backend": backend, "config": {"format": "json"}}},
        safety={"redaction_enabled": True, "safe_errors": True},
    )
    return normalize_package_config(raw)


def test_enabled_event_sink_passes_and_invokes_hook() -> None:
    calls: list[tuple[object, object]] = []

    def validate_config(*, config: object, context: object) -> None:
        calls.append((config, context))

    registry = PluginRegistry([_sink_plugin(validate_config=validate_config, create_sink=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("create_sink should not be called")))])
    validator = ConfigValidator(registry)
    config = _normalized_config(enabled_plugins=("sink-plugin",))

    validated = validator.validate(config)

    assert validated.normalized is config
    assert len(calls) == 1
    assert calls[0][0].backend == "stdout"


def test_unknown_event_sink_fails() -> None:
    registry = PluginRegistry([_sink_plugin()])
    validator = ConfigValidator(registry)
    config = _normalized_config(enabled_plugins=(), backend="stdout")

    with pytest.raises(PluginResolutionError) as excinfo:
        validator.validate(config)

    assert excinfo.value.code == "PLUGIN_UNKNOWN_EVENT_SINK"
    assert excinfo.value.metadata == {"backend": "stdout"}


def test_empty_event_sink_mapping_is_allowed() -> None:
    registry = PluginRegistry([_sink_plugin()])
    validator = ConfigValidator(registry)
    raw = RawPackageConfig(
        version=1,
        plugins={"enabled": ("sink-plugin",)},
        providers={},
        tools={"allowlist": ()},
        stores={},
        event_sinks={},
        safety={"redaction_enabled": True, "safe_errors": True},
    )
    config = normalize_package_config(raw)

    validated = validator.validate(config)

    assert validated.effective_plugins.plugin_names == ("sink-plugin",)


def test_event_sink_validation_hook_arbitrary_exception_is_wrapped() -> None:
    def validate_config(*, config: object, context: object) -> None:
        raise ValueError("boom")

    registry = PluginRegistry([_sink_plugin(validate_config=validate_config)])
    validator = ConfigValidator(registry)
    config = _normalized_config(enabled_plugins=("sink-plugin",))

    with pytest.raises(PluginValidationError) as excinfo:
        validator.validate(config)

    assert excinfo.value.code == "PLUGIN_VALIDATION_FAILED"
    assert isinstance(excinfo.value.__cause__, ValueError)


def test_event_sink_validation_does_not_call_factory_hook() -> None:
    def create_sink(*args, **kwargs):
        raise AssertionError("create_sink should not be called")

    registry = PluginRegistry([_sink_plugin(validate_config=lambda **kwargs: None, create_sink=create_sink)])
    validator = ConfigValidator(registry)
    config = _normalized_config(enabled_plugins=("sink-plugin",))

    validator.validate(config)
