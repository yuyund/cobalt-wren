"""Public workflow-integration vocabulary.

This module defines framework-neutral contracts used by official OSS helpers.
It does not discover, import, or execute any concrete workflow framework.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol, runtime_checkable

__all__ = [
    "IntegrationSupport",
    "IntegrationMaturity",
    "IntegrationAvailabilityStatus",
    "ActionSafety",
    "ProjectionOwnerKind",
    "IntegrationCapability",
    "IntegrationDefinition",
    "IntegrationAvailability",
    "IntegrationContext",
    "ExecutionUnitProjection",
    "LifecycleProjection",
    "IntegrationProjection",
    "IntegrationActionDescriptor",
    "IntegrationActionRequest",
    "IntegrationProjectionBatch",
    "WorkflowIntegrationProvider",
]


def _copy_mapping(value: Mapping[str, object] | None) -> dict[str, object]:
    return dict(value or {})


def _required_text(value: str, *, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be blank")
    return normalized


class IntegrationSupport(StrEnum):
    NONE = "none"
    PARTIAL = "partial"
    FULL = "full"


class IntegrationMaturity(StrEnum):
    EXPERIMENTAL = "experimental"
    PREVIEW = "preview"
    STABLE = "stable"


class IntegrationAvailabilityStatus(StrEnum):
    AVAILABLE = "available"
    NOT_INSTALLED = "not_installed"
    VERSION_INCOMPATIBLE = "version_incompatible"
    PROVIDER_INVALID = "provider_invalid"


class ActionSafety(StrEnum):
    READ_ONLY = "read_only"
    MUTATING = "mutating"
    DESTRUCTIVE = "destructive"


class ProjectionOwnerKind(StrEnum):
    RUN = "run"
    EXECUTION_UNIT = "execution_unit"
    INTERACTION = "interaction"
    ARTIFACT = "artifact"
    CHECKPOINT = "checkpoint"


@dataclass(frozen=True, slots=True)
class IntegrationCapability:
    name: str
    support: IntegrationSupport = IntegrationSupport.FULL
    limitations: tuple[str, ...] = ()
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _required_text(self.name, field_name="capability name"))
        object.__setattr__(self, "limitations", tuple(self.limitations))
        object.__setattr__(self, "metadata", _copy_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class IntegrationDefinition:
    integration_id: str
    distribution: str
    import_name: str
    provider_path: str
    supported_versions: str = ""
    maturity: IntegrationMaturity = IntegrationMaturity.EXPERIMENTAL
    detection_priority: int = 0
    capabilities: tuple[IntegrationCapability, ...] = ()
    limitations: tuple[str, ...] = ()
    documentation_ref: str = ""
    auto_detection: bool = False
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "integration_id", _required_text(self.integration_id, field_name="integration_id"))
        object.__setattr__(self, "distribution", _required_text(self.distribution, field_name="distribution"))
        object.__setattr__(self, "import_name", _required_text(self.import_name, field_name="import_name"))
        provider_path = _required_text(self.provider_path, field_name="provider_path")
        if provider_path.count(":") != 1:
            raise ValueError("provider_path must use 'module:attribute' form")
        object.__setattr__(self, "provider_path", provider_path)
        capabilities = tuple(self.capabilities)
        names = [capability.name for capability in capabilities]
        if len(names) != len(set(names)):
            raise ValueError("integration capability names must be unique")
        object.__setattr__(self, "capabilities", capabilities)
        object.__setattr__(self, "limitations", tuple(self.limitations))
        object.__setattr__(self, "metadata", _copy_mapping(self.metadata))

    def capability(self, name: str) -> IntegrationCapability | None:
        return next((item for item in self.capabilities if item.name == name), None)


@dataclass(frozen=True, slots=True)
class IntegrationAvailability:
    integration_id: str
    status: IntegrationAvailabilityStatus
    installed_version: str | None = None
    supported_versions: str = ""
    reason: str = ""

    @property
    def available(self) -> bool:
        return self.status is IntegrationAvailabilityStatus.AVAILABLE


@dataclass(frozen=True, slots=True)
class IntegrationContext:
    workflow_kind: str
    config: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "workflow_kind", _required_text(self.workflow_kind, field_name="workflow_kind"))
        object.__setattr__(self, "config", _copy_mapping(self.config))


@dataclass(frozen=True, slots=True)
class ExecutionUnitProjection:
    external_id: str
    semantic_kind: str
    integration_kind: str
    name: str
    status: str
    parent_external_id: str | None = None
    attempt: int = 1
    attributes: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name in ("external_id", "semantic_kind", "integration_kind", "name", "status"):
            object.__setattr__(self, field_name, _required_text(getattr(self, field_name), field_name=field_name))
        if self.parent_external_id is not None:
            object.__setattr__(self, "parent_external_id", _required_text(self.parent_external_id, field_name="parent_external_id"))
        if self.attempt < 1:
            raise ValueError("attempt must be at least 1")
        object.__setattr__(self, "attributes", _copy_mapping(self.attributes))


@dataclass(frozen=True, slots=True)
class LifecycleProjection:
    external_id: str
    event_type: str
    status: str
    occurred_at: str
    attributes: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name in ("external_id", "event_type", "status", "occurred_at"):
            object.__setattr__(self, field_name, _required_text(getattr(self, field_name), field_name=field_name))
        object.__setattr__(self, "attributes", _copy_mapping(self.attributes))


@dataclass(frozen=True, slots=True)
class IntegrationProjection:
    schema_id: str
    owner_kind: ProjectionOwnerKind
    owner_external_id: str
    payload: Mapping[str, object] = field(default_factory=dict)
    retention_class: str = "diagnostic"
    max_payload_bytes: int = 65_536
    searchable_fields: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_id", _required_text(self.schema_id, field_name="schema_id"))
        object.__setattr__(self, "owner_external_id", _required_text(self.owner_external_id, field_name="owner_external_id"))
        object.__setattr__(self, "retention_class", _required_text(self.retention_class, field_name="retention_class"))
        if self.max_payload_bytes < 1:
            raise ValueError("max_payload_bytes must be positive")
        object.__setattr__(self, "payload", _copy_mapping(self.payload))
        object.__setattr__(self, "searchable_fields", tuple(self.searchable_fields))


@dataclass(frozen=True, slots=True)
class IntegrationActionDescriptor:
    action_id: str
    target_kind: str
    label: str
    input_schema: Mapping[str, object] = field(default_factory=dict)
    safety: ActionSafety = ActionSafety.MUTATING
    available: bool = True
    unavailable_reason: str = ""
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name in ("action_id", "target_kind", "label"):
            object.__setattr__(self, field_name, _required_text(getattr(self, field_name), field_name=field_name))
        if self.available and self.unavailable_reason:
            raise ValueError("available actions must not define unavailable_reason")
        object.__setattr__(self, "input_schema", _copy_mapping(self.input_schema))
        object.__setattr__(self, "metadata", _copy_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class IntegrationActionRequest:
    action_id: str
    target_kind: str
    target_external_id: str
    payload: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name in ("action_id", "target_kind", "target_external_id"):
            object.__setattr__(self, field_name, _required_text(getattr(self, field_name), field_name=field_name))
        object.__setattr__(self, "payload", _copy_mapping(self.payload))


@dataclass(frozen=True, slots=True)
class IntegrationProjectionBatch:
    execution_units: tuple[ExecutionUnitProjection, ...] = ()
    lifecycle: tuple[LifecycleProjection, ...] = ()
    integration_projections: tuple[IntegrationProjection, ...] = ()
    actions: tuple[IntegrationActionDescriptor, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "execution_units", tuple(self.execution_units))
        object.__setattr__(self, "lifecycle", tuple(self.lifecycle))
        object.__setattr__(self, "integration_projections", tuple(self.integration_projections))
        object.__setattr__(self, "actions", tuple(self.actions))


@runtime_checkable
class WorkflowIntegrationProvider(Protocol):
    @property
    def definition(self) -> IntegrationDefinition: ...

    def wrap(self, target: object, *, context: IntegrationContext) -> object: ...
