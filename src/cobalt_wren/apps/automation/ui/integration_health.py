"""Renderer-neutral workflow integration availability and health specs."""

from __future__ import annotations

from dataclasses import dataclass

from cobalt_wren.api.errors import PluginResolutionError
from cobalt_wren.api.integrations import (
    IntegrationCapability,
    IntegrationDefinition,
)
from cobalt_wren.integrations.workflows.registry import (
    WorkflowIntegrationRegistry,
    create_supported_workflow_integration_registry,
)


@dataclass(frozen=True, slots=True)
class IntegrationCapabilityHealthSpec:
    name: str
    support: str
    limitations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class IntegrationHealthSpec:
    integration_id: str
    distribution: str
    import_name: str
    maturity: str
    status: str
    installed_version: str
    supported_versions: str
    provider_status: str
    diagnostic: str
    install_extra: str
    install_command: str
    auto_detection: bool
    documentation_ref: str
    capabilities: tuple[IntegrationCapabilityHealthSpec, ...]
    limitations: tuple[str, ...]

    @property
    def available(self) -> bool:
        return self.status == "available" and self.provider_status == "loaded"

    @property
    def health_status(self) -> str:
        if self.available:
            return "ready"
        if self.status != "available":
            return self.status
        return self.provider_status


@dataclass(frozen=True, slots=True)
class IntegrationHealthListSpec:
    title: str
    integrations: tuple[IntegrationHealthSpec, ...]

    @property
    def available_count(self) -> int:
        return sum(item.available for item in self.integrations)


def build_integration_health_list(
    registry: WorkflowIntegrationRegistry | None = None,
) -> IntegrationHealthListSpec:
    active_registry = registry or create_supported_workflow_integration_registry()
    items = tuple(
        _build_health(active_registry, definition)
        for definition in sorted(
            active_registry.list_definitions(),
            key=lambda item: (-item.detection_priority, item.integration_id),
        )
    )
    return IntegrationHealthListSpec(title="Workflow integrations", integrations=items)


def build_integration_health_detail(
    integration_id: str,
    registry: WorkflowIntegrationRegistry | None = None,
) -> IntegrationHealthSpec:
    active_registry = registry or create_supported_workflow_integration_registry()
    return _build_health(active_registry, active_registry.get_definition(integration_id))


def _build_health(
    registry: WorkflowIntegrationRegistry,
    definition: IntegrationDefinition,
) -> IntegrationHealthSpec:
    availability = registry.inspect(definition.integration_id)
    provider_status = "not_checked"
    diagnostic = availability.reason
    if availability.available:
        try:
            registry.resolve(definition.integration_id)
        except PluginResolutionError as exc:
            provider_status = _provider_status(exc.code)
            diagnostic = _provider_diagnostic(exc.code)
        else:
            provider_status = "loaded"
    extra = str(definition.metadata.get("install_extra", "")).strip()
    install_command = (
        f'pip install "cobalt-wren[{extra}]"' if extra else ""
    )
    return IntegrationHealthSpec(
        integration_id=definition.integration_id,
        distribution=definition.distribution,
        import_name=definition.import_name,
        maturity=definition.maturity.value,
        status=availability.status.value,
        installed_version=availability.installed_version or "",
        supported_versions=availability.supported_versions,
        provider_status=provider_status,
        diagnostic=diagnostic,
        install_extra=extra,
        install_command=install_command,
        auto_detection=definition.auto_detection,
        documentation_ref=definition.documentation_ref,
        capabilities=tuple(_capability_spec(item) for item in definition.capabilities),
        limitations=definition.limitations,
    )


def _capability_spec(
    capability: IntegrationCapability,
) -> IntegrationCapabilityHealthSpec:
    return IntegrationCapabilityHealthSpec(
        name=capability.name,
        support=capability.support.value,
        limitations=capability.limitations,
    )


def _provider_status(code: str) -> str:
    if code == "WORKFLOW_INTEGRATION_PROVIDER_INVALID":
        return "invalid"
    if code == "WORKFLOW_INTEGRATION_DEFINITION_MISMATCH":
        return "definition_mismatch"
    return "load_failed"


def _provider_diagnostic(code: str) -> str:
    diagnostics = {
        "WORKFLOW_INTEGRATION_PROVIDER_INVALID": (
            "The configured provider does not implement the workflow integration contract."
        ),
        "WORKFLOW_INTEGRATION_DEFINITION_MISMATCH": (
            "The loaded provider definition does not match the central definition."
        ),
        "WORKFLOW_INTEGRATION_PROVIDER_LOAD_FAILED": (
            "The provider module could not be loaded. Review installation and compatibility."
        ),
    }
    return diagnostics.get(code, "The provider could not be resolved safely.")
