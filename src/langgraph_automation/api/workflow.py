"""Public workflow vocabulary facade for langgraph-automation."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "WorkflowMetadata",
    "WorkflowRequirements",
    "WorkflowDefinition",
    "WorkflowContribution",
]


def _copy_mapping(mapping: Mapping[str, Any] | None) -> dict[str, Any]:
    return dict(mapping or {})


def _tupleize_strs(values: object) -> tuple[str, ...]:
    if isinstance(values, tuple):
        return values
    return tuple(values)  # type: ignore[arg-type]


@dataclass(frozen=True, slots=True)
class WorkflowMetadata:
    name: str
    description: str = ""
    version: str = "0.1.0"
    tags: tuple[str, ...] = ()
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "tags", _tupleize_strs(self.tags))
        object.__setattr__(self, "metadata", _copy_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class WorkflowRequirements:
    provider_profiles: tuple[str, ...] = ()
    tools: tuple[str, ...] = ()
    artifact_store: bool = False
    checkpoint_store: bool = False
    event_sinks: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "provider_profiles", _tupleize_strs(self.provider_profiles))
        object.__setattr__(self, "tools", _tupleize_strs(self.tools))
        object.__setattr__(self, "event_sinks", _tupleize_strs(self.event_sinks))


@dataclass(frozen=True, slots=True)
class WorkflowDefinition:
    kind: str
    metadata: WorkflowMetadata
    requirements: WorkflowRequirements
    build: Callable[..., object]
    input_schema: Mapping[str, object] | None = None
    output_schema: Mapping[str, object] | None = None
    extra: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "input_schema", None if self.input_schema is None else _copy_mapping(self.input_schema))
        object.__setattr__(self, "output_schema", None if self.output_schema is None else _copy_mapping(self.output_schema))
        object.__setattr__(self, "extra", _copy_mapping(self.extra))


@dataclass(frozen=True, slots=True)
class WorkflowContribution:
    kind: str
    definition: WorkflowDefinition
    validate_config: Callable[..., None] | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", _copy_mapping(self.metadata))
