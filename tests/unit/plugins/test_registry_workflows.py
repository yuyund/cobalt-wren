"""PluginRegistry workflow tests."""

from __future__ import annotations

import pytest

from cobalt_wren.api.errors import PluginRegistrationError, PluginResolutionError
from cobalt_wren.api.plugins import Plugin, PluginContributions, PluginMetadata
from cobalt_wren.api.workflow import WorkflowContribution, WorkflowDefinition, WorkflowMetadata, WorkflowRequirements
from cobalt_wren.plugins.registry import PluginRegistry


def _build_workflow_plugin(
    name: str,
    *,
    workflow_kind: str,
    validate_marker: list[str] | None = None,
    build_marker: list[str] | None = None,
) -> Plugin:
    def _validate(*args, **kwargs):
        if validate_marker is not None:
            validate_marker.append(name)
        raise AssertionError("workflow validate_config should not be called during registration")

    def _build(*args, **kwargs):
        if build_marker is not None:
            build_marker.append(name)
        raise AssertionError("workflow build should not be called during registration")

    contribution = WorkflowContribution(
        kind=workflow_kind,
        definition=WorkflowDefinition(
            kind=workflow_kind,
            metadata=WorkflowMetadata(name=workflow_kind, description="Workflow"),
            requirements=WorkflowRequirements(provider_profiles=("default",), tools=("github.search_issues",)),
            build=_build,
        ),
        validate_config=_validate,
    )

    return Plugin(
        metadata=PluginMetadata(name=name, version="0.1.0", plugin_types=("workflow",)),
        contributions=PluginContributions(workflows=(contribution,)),
    )


def test_registry_registers_and_looks_up_workflows() -> None:
    registry = PluginRegistry()
    plugin = _build_workflow_plugin("company-agent-plugin", workflow_kind="company_agent")

    registry.register(plugin)

    assert registry.get_workflow("company_agent") is plugin.contributions.workflows[0]
    assert registry.get_plugin("company-agent-plugin") is plugin


def test_registry_rejects_duplicate_workflow_kind() -> None:
    registry = PluginRegistry()
    registry.register(_build_workflow_plugin("company-agent-plugin", workflow_kind="company_agent"))

    with pytest.raises(PluginRegistrationError) as excinfo:
        registry.register(_build_workflow_plugin("alternate-agent-plugin", workflow_kind="company_agent"))

    assert excinfo.value.code == "PLUGIN_CONTRIBUTION_CONFLICT"
    assert excinfo.value.component == "plugin_registry"
    assert excinfo.value.metadata["contribution_scope"] == "workflow"
    assert excinfo.value.metadata["contribution_name"] == "company_agent"


def test_registry_raises_resolution_error_for_unknown_workflow() -> None:
    registry = PluginRegistry()

    with pytest.raises(PluginResolutionError) as excinfo:
        registry.get_workflow("missing_workflow")

    assert excinfo.value.code == "PLUGIN_UNKNOWN_WORKFLOW"
    assert excinfo.value.component == "plugin_registry"


def test_registry_does_not_call_workflow_hooks_during_registration() -> None:
    validate_calls: list[str] = []
    build_calls: list[str] = []
    registry = PluginRegistry()
    plugin = _build_workflow_plugin(
        "company-agent-plugin",
        workflow_kind="company_agent",
        validate_marker=validate_calls,
        build_marker=build_calls,
    )

    registry.register(plugin)

    assert validate_calls == []
    assert build_calls == []
