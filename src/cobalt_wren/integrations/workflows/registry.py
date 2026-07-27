"""Internal registry for explicit workflow OSS integration selection."""

from __future__ import annotations

from collections.abc import Iterable
from importlib import import_module, metadata as importlib_metadata, util as importlib_util
from typing import cast

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version

from cobalt_wren.api.errors import PluginRegistrationError, PluginResolutionError
from cobalt_wren.api.integrations import (
    IntegrationAvailability,
    IntegrationAvailabilityStatus,
    IntegrationContext,
    IntegrationDefinition,
    WorkflowIntegrationProvider,
)

_COMPONENT = "workflow_integration_registry"


class WorkflowIntegrationRegistry:
    """Stores integration definitions and resolves providers only on demand."""

    def __init__(
        self,
        definitions: Iterable[IntegrationDefinition] = (),
        *,
        providers: Iterable[WorkflowIntegrationProvider] = (),
    ) -> None:
        self._definitions: dict[str, IntegrationDefinition] = {}
        self._providers: dict[str, WorkflowIntegrationProvider] = {}
        for definition in definitions:
            self.register_definition(definition)
        for provider in providers:
            self.register_provider(provider)

    def register_definition(self, definition: IntegrationDefinition) -> None:
        integration_id = definition.integration_id
        if integration_id in self._definitions:
            raise PluginRegistrationError(
                f"Workflow integration registration failed: duplicate integration '{integration_id}'.",
                code="WORKFLOW_INTEGRATION_DUPLICATE",
                component=_COMPONENT,
                metadata={"integration_id": integration_id},
            )
        self._definitions[integration_id] = definition

    def register_provider(self, provider: WorkflowIntegrationProvider) -> None:
        definition = provider.definition
        existing = self._definitions.get(definition.integration_id)
        if existing is None:
            self.register_definition(definition)
        elif existing != definition:
            raise PluginRegistrationError(
                "Workflow integration registration failed: provider definition does not match the registered definition.",
                code="WORKFLOW_INTEGRATION_DEFINITION_MISMATCH",
                component=_COMPONENT,
                metadata={"integration_id": definition.integration_id},
            )
        if definition.integration_id in self._providers:
            raise PluginRegistrationError(
                f"Workflow integration registration failed: duplicate provider '{definition.integration_id}'.",
                code="WORKFLOW_INTEGRATION_PROVIDER_DUPLICATE",
                component=_COMPONENT,
                metadata={"integration_id": definition.integration_id},
            )
        self._providers[definition.integration_id] = provider

    def list_definitions(self) -> tuple[IntegrationDefinition, ...]:
        return tuple(self._definitions.values())

    def get_definition(self, integration_id: str) -> IntegrationDefinition:
        try:
            return self._definitions[integration_id]
        except KeyError as exc:
            raise PluginResolutionError(
                f"Workflow integration '{integration_id}' is not registered.",
                code="WORKFLOW_INTEGRATION_UNKNOWN",
                component=_COMPONENT,
                metadata={"integration_id": integration_id},
            ) from exc

    def inspect(self, integration_id: str) -> IntegrationAvailability:
        definition = self.get_definition(integration_id)
        if importlib_util.find_spec(definition.import_name) is None:
            return IntegrationAvailability(
                integration_id=integration_id,
                status=IntegrationAvailabilityStatus.NOT_INSTALLED,
                supported_versions=definition.supported_versions,
                reason="target import is unavailable",
            )
        try:
            installed_version = importlib_metadata.version(definition.distribution)
        except importlib_metadata.PackageNotFoundError:
            return IntegrationAvailability(
                integration_id=integration_id,
                status=IntegrationAvailabilityStatus.NOT_INSTALLED,
                supported_versions=definition.supported_versions,
                reason="target distribution is unavailable",
            )
        if definition.supported_versions and not _version_matches(installed_version, definition.supported_versions):
            return IntegrationAvailability(
                integration_id=integration_id,
                status=IntegrationAvailabilityStatus.VERSION_INCOMPATIBLE,
                installed_version=installed_version,
                supported_versions=definition.supported_versions,
                reason="installed version is outside the supported range",
            )
        return IntegrationAvailability(
            integration_id=integration_id,
            status=IntegrationAvailabilityStatus.AVAILABLE,
            installed_version=installed_version,
            supported_versions=definition.supported_versions,
        )

    def resolve(self, integration_id: str) -> WorkflowIntegrationProvider:
        availability = self.inspect(integration_id)
        if not availability.available:
            raise PluginResolutionError(
                f"Workflow integration '{integration_id}' is unavailable.",
                code=(
                    "WORKFLOW_INTEGRATION_VERSION_INCOMPATIBLE"
                    if availability.status is IntegrationAvailabilityStatus.VERSION_INCOMPATIBLE
                    else "WORKFLOW_INTEGRATION_NOT_INSTALLED"
                ),
                component=_COMPONENT,
                metadata={
                    "integration_id": integration_id,
                    "installed_version": availability.installed_version,
                    "supported_versions": availability.supported_versions,
                },
            )
        provider = self._providers.get(integration_id)
        if provider is None:
            provider = self._load_provider(self.get_definition(integration_id))
            self._providers[integration_id] = provider
        return provider

    def wrap(self, integration_id: str, target: object, *, context: IntegrationContext) -> object:
        return self.resolve(integration_id).wrap(target, context=context)

    @staticmethod
    def _load_provider(definition: IntegrationDefinition) -> WorkflowIntegrationProvider:
        module_name, attribute_name = definition.provider_path.split(":", 1)
        try:
            loaded = getattr(import_module(module_name), attribute_name)
            provider = loaded() if isinstance(loaded, type) else loaded
        except Exception as exc:
            raise PluginResolutionError(
                f"Workflow integration '{definition.integration_id}' provider could not be loaded.",
                code="WORKFLOW_INTEGRATION_PROVIDER_LOAD_FAILED",
                component=_COMPONENT,
                metadata={"integration_id": definition.integration_id},
            ) from exc
        if not isinstance(provider, WorkflowIntegrationProvider):
            raise PluginResolutionError(
                f"Workflow integration '{definition.integration_id}' provider is invalid.",
                code="WORKFLOW_INTEGRATION_PROVIDER_INVALID",
                component=_COMPONENT,
                metadata={"integration_id": definition.integration_id},
            )
        if provider.definition != definition:
            raise PluginResolutionError(
                f"Workflow integration '{definition.integration_id}' provider definition does not match the registry.",
                code="WORKFLOW_INTEGRATION_DEFINITION_MISMATCH",
                component=_COMPONENT,
                metadata={"integration_id": definition.integration_id},
            )
        return cast(WorkflowIntegrationProvider, provider)


def create_supported_workflow_integration_registry() -> WorkflowIntegrationRegistry:
    """Create a registry from the centrally managed supported OSS definitions."""

    from cobalt_wren.integrations.workflows.definitions import (
        SUPPORTED_WORKFLOW_INTEGRATIONS,
    )

    return WorkflowIntegrationRegistry(SUPPORTED_WORKFLOW_INTEGRATIONS)


def _version_matches(installed_version: str, supported_versions: str) -> bool:
    try:
        return Version(installed_version) in SpecifierSet(supported_versions)
    except (InvalidVersion, InvalidSpecifier) as exc:
        raise PluginResolutionError(
            "Workflow integration version metadata is invalid.",
            code="WORKFLOW_INTEGRATION_VERSION_METADATA_INVALID",
            component=_COMPONENT,
        ) from exc
