"""Package engine creation tests."""

from __future__ import annotations

import pytest

from cobalt_wren.api.engine import AutomationEngine, create_engine
from cobalt_wren.api.errors import ConfigError, PluginRegistrationError
from cobalt_wren.api.plugins import Plugin, PluginContributions, PluginMetadata
from cobalt_wren.api.workflow import WorkflowContribution, WorkflowDefinition, WorkflowMetadata, WorkflowRequirements


def _base_config() -> dict[str, object]:
    return {
        "version": 1,
        "environment": "test",
    }


def _minimal_reference_config() -> dict[str, object]:
    return {
        "version": 1,
        "environment": "test",
        "providers": {
            "default": {
                "provider": "litellm",
                "model": "gpt-4.1-mini",
                "secrets": {
                    "api_key": {
                        "source": "env",
                        "name": "OPENAI_API_KEY",
                    },
                },
            },
        },
        "tools": {
            "allowlist": ["echo"],
        },
    }


def _custom_workflow_plugin() -> Plugin:
    contribution = WorkflowContribution(
        kind="custom.workflow",
        definition=WorkflowDefinition(
            kind="custom.workflow",
            metadata=WorkflowMetadata(name="Custom Workflow"),
            requirements=WorkflowRequirements(),
            build=lambda: {"graph": "custom"},
        ),
    )
    return Plugin(
        metadata=PluginMetadata(
            name="custom.workflow.plugin",
            version="0.1.0",
            plugin_types=("workflow",),
        ),
        contributions=PluginContributions(workflows=(contribution,)),
    )


def test_create_engine_builds_engine_from_mapping_and_hides_internal_state() -> None:
    engine = create_engine(_base_config())

    assert isinstance(engine, AutomationEngine)
    assert not hasattr(engine, "registry")
    assert not hasattr(engine, "dependencies")
    assert not hasattr(engine, "validated_config")
    assert not hasattr(engine, "preparer")


def test_create_engine_accepts_explicit_plugins() -> None:
    engine = create_engine(_base_config(), plugins=(_custom_workflow_plugin(),))

    prepared = engine.prepare_workflow("custom.workflow")

    assert prepared.kind == "custom.workflow"
    assert prepared.executable == {"graph": "custom"}


def test_create_engine_raises_on_duplicate_plugin_names() -> None:
    first = _custom_workflow_plugin()
    second = _custom_workflow_plugin()

    with pytest.raises(PluginRegistrationError) as excinfo:
        create_engine(_base_config(), plugins=(first, second))

    assert excinfo.value.code == "PLUGIN_DUPLICATE_NAME"
    assert excinfo.value.component == "plugin_registry"


def test_create_engine_rejects_invalid_config() -> None:
    with pytest.raises(ConfigError) as excinfo:
        create_engine({"version": 2})

    assert excinfo.value.code == "CONFIG_UNSUPPORTED_VERSION"
    assert excinfo.value.component == "config_loader"
