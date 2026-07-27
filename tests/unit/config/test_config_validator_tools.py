"""Config validator tool resolution tests."""

from __future__ import annotations

import pytest

from cobalt_wren.api.errors import ConfigError, PluginResolutionError, PluginValidationError
from cobalt_wren.api.plugins import Plugin, PluginContributions, PluginMetadata, ToolContribution
from cobalt_wren.config.models import NormalizedPackageConfig, RawPackageConfig
from cobalt_wren.config.normalizer import normalize_package_config
from cobalt_wren.config.validator import ConfigValidator
from cobalt_wren.plugins.registry import PluginRegistry


def _tool_plugin(*, validate_config=None, create_tool=None) -> Plugin:
    return Plugin(
        metadata=PluginMetadata(name="tool-plugin", version="0.1.0", plugin_types=("tool",)),
        contributions=PluginContributions(
            tools=(
                ToolContribution(
                    name="github.search_issues",
                    validate_config=validate_config,
                    create_tool=create_tool,
                ),
            ),
        ),
    )


def _normalized_config(*, enabled_plugins: tuple[str, ...], allowlist: tuple[str, ...], configs: dict[str, object] | None = None) -> NormalizedPackageConfig:
    raw = RawPackageConfig(
        version=1,
        plugins={"enabled": enabled_plugins},
        providers={},
        tools={"allowlist": allowlist, "configs": configs or {}},
        stores={},
        event_sinks={},
        safety={"redaction_enabled": True, "safe_errors": True},
    )
    return normalize_package_config(raw)


def test_allowlisted_enabled_tool_passes_and_invokes_hook() -> None:
    calls: list[tuple[dict[str, object], object]] = []

    def validate_config(*, config: dict[str, object], context: object) -> None:
        calls.append((config, context))

    registry = PluginRegistry([_tool_plugin(validate_config=validate_config, create_tool=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("create_tool should not be called")))])
    validator = ConfigValidator(registry)
    config = _normalized_config(enabled_plugins=("tool-plugin",), allowlist=("github.search_issues",))

    validated = validator.validate(config)

    assert validated.normalized is config
    assert len(calls) == 1
    assert calls[0][0] == {}


def test_registered_but_disabled_tool_fails() -> None:
    registry = PluginRegistry([_tool_plugin()])
    validator = ConfigValidator(registry)
    config = _normalized_config(enabled_plugins=(), allowlist=("github.search_issues",))

    with pytest.raises(PluginResolutionError) as excinfo:
        validator.validate(config)

    assert excinfo.value.code == "PLUGIN_UNKNOWN_TOOL"
    assert excinfo.value.metadata == {"tool_name": "github.search_issues"}


def test_unknown_tool_fails() -> None:
    registry = PluginRegistry([_tool_plugin()])
    validator = ConfigValidator(registry)
    config = _normalized_config(enabled_plugins=("tool-plugin",), allowlist=("missing.tool",))

    with pytest.raises(PluginResolutionError) as excinfo:
        validator.validate(config)

    assert excinfo.value.code == "PLUGIN_UNKNOWN_TOOL"
    assert excinfo.value.metadata == {"tool_name": "missing.tool"}


def test_empty_tool_allowlist_is_allowed() -> None:
    registry = PluginRegistry([_tool_plugin()])
    validator = ConfigValidator(registry)
    config = _normalized_config(enabled_plugins=("tool-plugin",), allowlist=())

    validated = validator.validate(config)

    assert validated.effective_plugins.plugin_names == ("tool-plugin",)


def test_tool_configs_outside_allowlist_raise_config_error() -> None:
    registry = PluginRegistry([_tool_plugin()])
    validator = ConfigValidator(registry)
    config = _normalized_config(
        enabled_plugins=("tool-plugin",),
        allowlist=("github.search_issues",),
        configs={"github.create_issue": {"timeout_seconds": 10}},
    )

    with pytest.raises(ConfigError) as excinfo:
        validator.validate(config)

    assert excinfo.value.code == "CONFIG_TOOL_CONFIG_NOT_ALLOWED"
    assert excinfo.value.component == "config_validator"
    assert excinfo.value.metadata == {"tool_name": "github.create_issue"}


def test_allowlisted_tool_config_is_passed_to_hook() -> None:
    calls: list[dict[str, object]] = []

    def validate_config(*, config: dict[str, object], context: object) -> None:
        calls.append(config)

    registry = PluginRegistry([_tool_plugin(validate_config=validate_config)])
    validator = ConfigValidator(registry)
    config = _normalized_config(
        enabled_plugins=("tool-plugin",),
        allowlist=("github.search_issues",),
        configs={"github.search_issues": {"timeout_seconds": 10}},
    )

    validator.validate(config)

    assert calls == [{"timeout_seconds": 10}]


def test_tool_validation_hook_arbitrary_exception_is_wrapped() -> None:
    def validate_config(*, config: dict[str, object], context: object) -> None:
        raise ValueError("boom")

    registry = PluginRegistry([_tool_plugin(validate_config=validate_config)])
    validator = ConfigValidator(registry)
    config = _normalized_config(enabled_plugins=("tool-plugin",), allowlist=("github.search_issues",))

    with pytest.raises(PluginValidationError) as excinfo:
        validator.validate(config)

    assert excinfo.value.code == "PLUGIN_VALIDATION_FAILED"
    assert isinstance(excinfo.value.__cause__, ValueError)


def test_tool_validation_does_not_call_factory_hook() -> None:
    def create_tool(*args, **kwargs):
        raise AssertionError("create_tool should not be called")

    registry = PluginRegistry([_tool_plugin(validate_config=lambda **kwargs: None, create_tool=create_tool)])
    validator = ConfigValidator(registry)
    config = _normalized_config(enabled_plugins=("tool-plugin",), allowlist=("github.search_issues",))

    validator.validate(config)
