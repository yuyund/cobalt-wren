"""WorkflowIntegrationRegistry tests."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from cobalt_wren.api.errors import PluginRegistrationError, PluginResolutionError
from cobalt_wren.api.integrations import (
    IntegrationAvailabilityStatus,
    IntegrationContext,
    IntegrationDefinition,
)
from cobalt_wren.integrations.workflows.registry import (
    WorkflowIntegrationRegistry,
    create_supported_workflow_integration_registry,
)


DEFINITION = IntegrationDefinition(
    integration_id="pytest",
    distribution="pytest",
    import_name="pytest",
    provider_path="tests.unit.integrations.test_workflow_integration_registry:PROVIDER",
    supported_versions=">=1",
)


@dataclass(frozen=True)
class _Provider:
    definition: IntegrationDefinition = DEFINITION

    def wrap(self, target: object, *, context: IntegrationContext) -> object:
        return {"target": target, "workflow_kind": context.workflow_kind, "config": dict(context.config)}


PROVIDER = _Provider()


def test_registry_reports_installed_compatible_integration() -> None:
    registry = WorkflowIntegrationRegistry((DEFINITION,), providers=(PROVIDER,))

    availability = registry.inspect("pytest")

    assert availability.status is IntegrationAvailabilityStatus.AVAILABLE
    assert availability.installed_version


def test_registry_wraps_through_explicit_provider() -> None:
    registry = WorkflowIntegrationRegistry((DEFINITION,), providers=(PROVIDER,))

    wrapped = registry.wrap(
        "pytest",
        object(),
        context=IntegrationContext(workflow_kind="acme.review", config={"mode": "strict"}),
    )

    assert wrapped["workflow_kind"] == "acme.review"
    assert wrapped["config"] == {"mode": "strict"}


def test_registry_rejects_duplicate_definition() -> None:
    registry = WorkflowIntegrationRegistry((DEFINITION,))

    with pytest.raises(PluginRegistrationError) as excinfo:
        registry.register_definition(DEFINITION)

    assert excinfo.value.code == "WORKFLOW_INTEGRATION_DUPLICATE"


def test_registry_reports_missing_distribution_without_importing_provider() -> None:
    missing = IntegrationDefinition(
        integration_id="missing",
        distribution="definitely-not-installed-workflow-oss",
        import_name="definitely_not_installed_workflow_oss",
        provider_path="missing.provider:Provider",
    )
    registry = WorkflowIntegrationRegistry((missing,))

    availability = registry.inspect("missing")

    assert availability.status is IntegrationAvailabilityStatus.NOT_INSTALLED
    with pytest.raises(PluginResolutionError) as excinfo:
        registry.resolve("missing")
    assert excinfo.value.code == "WORKFLOW_INTEGRATION_NOT_INSTALLED"


def test_registry_reports_incompatible_version() -> None:
    incompatible = IntegrationDefinition(
        integration_id="pytest-future",
        distribution="pytest",
        import_name="pytest",
        provider_path="missing.provider:Provider",
        supported_versions=">9999",
    )
    registry = WorkflowIntegrationRegistry((incompatible,))

    availability = registry.inspect("pytest-future")

    assert availability.status is IntegrationAvailabilityStatus.VERSION_INCOMPATIBLE
    with pytest.raises(PluginResolutionError) as excinfo:
        registry.resolve("pytest-future")
    assert excinfo.value.code == "WORKFLOW_INTEGRATION_VERSION_INCOMPATIBLE"


def test_registry_unknown_integration_is_safe_resolution_error() -> None:
    registry = WorkflowIntegrationRegistry()

    with pytest.raises(PluginResolutionError) as excinfo:
        registry.get_definition("unknown")

    assert excinfo.value.code == "WORKFLOW_INTEGRATION_UNKNOWN"


def test_supported_registry_contains_lazy_langgraph_definition() -> None:
    registry = create_supported_workflow_integration_registry()

    definition = registry.get_definition("langgraph")
    availability = registry.inspect("langgraph")

    assert definition.integration_id == "langgraph"
    assert availability.available is True
    assert registry.resolve("langgraph").definition == definition


def test_supported_registry_contains_lazy_llamaindex_definition() -> None:
    registry = create_supported_workflow_integration_registry()

    definition = registry.get_definition("llamaindex-workflows")
    availability = registry.inspect("llamaindex-workflows")

    assert definition.integration_id == "llamaindex-workflows"
    assert availability.available is True
    assert registry.resolve("llamaindex-workflows").definition == definition
