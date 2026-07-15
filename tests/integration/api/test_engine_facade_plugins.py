"""Package engine facade explicit plugin tests."""

from __future__ import annotations

import pytest

from langgraph_automation.api.engine import AutomationEngine, EnginePreparedWorkflow, create_engine
from langgraph_automation.api.errors import PluginRegistrationError
from langgraph_automation.api.plugins import Plugin, PluginContributions, PluginMetadata, ProviderContribution
from langgraph_automation.api.workflow import WorkflowContribution, WorkflowDefinition, WorkflowMetadata, WorkflowRequirements


def _engine_config() -> dict[str, object]:
    return {
        "version": 1,
        "environment": "test",
        "providers": {
            "default": {
                "provider": "fake",
                "model": "test-model",
            },
        },
    }


def _custom_plugin(provider_calls: list[dict[str, object]] | None = None) -> Plugin:
    def create_client(*, config: object, context: object) -> object:
        if provider_calls is not None:
            provider_calls.append(
                {
                    "provider": getattr(config, "provider", None),
                    "model": getattr(config, "model", None),
                }
            )
        return {"client": getattr(config, "provider", None), "model": getattr(config, "model", None)}

    workflow = WorkflowContribution(
        kind="integration.custom_workflow",
        definition=WorkflowDefinition(
            kind="integration.custom_workflow",
            metadata=WorkflowMetadata(name="Custom Workflow", description="Smoke workflow for explicit plugins."),
            requirements=WorkflowRequirements(provider_profiles=("default",)),
            build=lambda: {"graph": "custom"},
        ),
    )
    provider = ProviderContribution(name="fake", provider_type="llm", create_client=create_client)
    return Plugin(
        metadata=PluginMetadata(name="integration.fake_plugin", version="0.1.0", plugin_types=("provider", "workflow")),
        contributions=PluginContributions(providers=(provider,), workflows=(workflow,)),
    )


def _workflow_only_plugin(plugin_name: str, workflow_kind: str) -> Plugin:
    return Plugin(
        metadata=PluginMetadata(name=plugin_name, version="0.1.0", plugin_types=("workflow",)),
        contributions=PluginContributions(
            workflows=(
                WorkflowContribution(
                    kind=workflow_kind,
                    definition=WorkflowDefinition(
                        kind=workflow_kind,
                        metadata=WorkflowMetadata(name=workflow_kind),
                        requirements=WorkflowRequirements(),
                        build=lambda: {"graph": workflow_kind},
                    ),
                ),
            ),
        ),
    )


def test_explicit_plugins_are_registered_and_auto_enabled_for_validation_and_assembly() -> None:
    provider_calls: list[dict[str, object]] = []
    engine = create_engine(_engine_config(), plugins=(_custom_plugin(provider_calls),))

    assert isinstance(engine, AutomationEngine)
    prepared = engine.prepare_workflow("integration.custom_workflow")

    assert isinstance(prepared, EnginePreparedWorkflow)
    assert prepared.kind == "integration.custom_workflow"
    assert prepared.graph == {"graph": "custom"}
    assert provider_calls == [{"provider": "fake", "model": "test-model"}]


def test_duplicate_explicit_workflow_kind_raises_plugin_registration_error() -> None:
    with pytest.raises(PluginRegistrationError) as excinfo:
        create_engine(
            {"version": 1, "environment": "test"},
            plugins=(
                _workflow_only_plugin("integration.plugin.a", "integration.duplicate_workflow"),
                _workflow_only_plugin("integration.plugin.b", "integration.duplicate_workflow"),
            ),
        )

    assert excinfo.value.code == "PLUGIN_CONTRIBUTION_CONFLICT"
    assert excinfo.value.component == "plugin_registry"
    assert excinfo.value.metadata["contribution_scope"] == "workflow"
    assert excinfo.value.metadata["contribution_name"] == "integration.duplicate_workflow"
