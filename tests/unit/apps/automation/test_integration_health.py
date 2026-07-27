"""Renderer-neutral integration availability and health tests."""

from __future__ import annotations

from dataclasses import dataclass

from cobalt_wren.api.integrations import (
    IntegrationContext,
    IntegrationDefinition,
)
from cobalt_wren.apps.automation.ui.integration_health import (
    build_integration_health_detail,
    build_integration_health_list,
)
from cobalt_wren.integrations.workflows.registry import (
    WorkflowIntegrationRegistry,
)


@dataclass(frozen=True)
class _Provider:
    definition: IntegrationDefinition

    def wrap(self, target: object, *, context: IntegrationContext) -> object:
        del context
        return target


AVAILABLE = IntegrationDefinition(
    integration_id="pytest-health",
    distribution="pytest",
    import_name="pytest",
    provider_path="unused:provider",
    supported_versions=">=1",
    metadata={"install_extra": "pytest-health"},
)


def test_health_list_reports_available_provider_and_install_extra() -> None:
    registry = WorkflowIntegrationRegistry(
        (AVAILABLE,), providers=(_Provider(AVAILABLE),)
    )

    page = build_integration_health_list(registry)

    assert page.available_count == 1
    item = page.integrations[0]
    assert item.status == "available"
    assert item.provider_status == "loaded"
    assert item.health_status == "ready"
    assert item.install_extra == "pytest-health"
    assert item.install_command == 'pip install "cobalt-wren[pytest-health]"'


def test_health_reports_missing_and_incompatible_without_loading_provider() -> None:
    missing = IntegrationDefinition(
        integration_id="missing-health",
        distribution="missing-health-distribution",
        import_name="missing_health_import",
        provider_path="private.failure:SECRET_VALUE",
        metadata={"install_extra": "missing-health"},
    )
    incompatible = IntegrationDefinition(
        integration_id="incompatible-health",
        distribution="pytest",
        import_name="pytest",
        provider_path="private.failure:SECRET_VALUE",
        supported_versions=">9999",
    )
    registry = WorkflowIntegrationRegistry((missing, incompatible))

    missing_health = build_integration_health_detail("missing-health", registry)
    incompatible_health = build_integration_health_detail(
        "incompatible-health", registry
    )

    assert missing_health.status == "not_installed"
    assert missing_health.provider_status == "not_checked"
    assert "SECRET_VALUE" not in missing_health.diagnostic
    assert incompatible_health.status == "version_incompatible"
    assert incompatible_health.provider_status == "not_checked"
    assert incompatible_health.installed_version


def test_health_sanitizes_provider_load_failure() -> None:
    broken = IntegrationDefinition(
        integration_id="broken-health",
        distribution="pytest",
        import_name="pytest",
        provider_path=(
            "tests.unit.apps.automation.test_integration_health:"
            "PrivateProviderFailure"
        ),
        supported_versions=">=1",
    )
    registry = WorkflowIntegrationRegistry((broken,))

    health = build_integration_health_detail("broken-health", registry)

    assert health.status == "available"
    assert health.provider_status == "load_failed"
    assert health.health_status == "load_failed"
    assert health.available is False
    assert "could not be loaded" in health.diagnostic
    assert "private-provider-secret" not in health.diagnostic
    assert "Traceback" not in health.diagnostic


class PrivateProviderFailure:
    def __init__(self) -> None:
        raise RuntimeError("private-provider-secret")
