"""Public plugin vocabulary facade for langgraph-automation."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from importlib import metadata as importlib_metadata
from typing import Any, TYPE_CHECKING

from langgraph_automation.api.errors import PluginResolutionError

if TYPE_CHECKING:
    from langgraph_automation.api.workflow import WorkflowContribution

__all__ = [
    'DEFAULT_PLUGIN_ENTRY_POINT_GROUP',
    'discover_plugins',
    'Plugin',
    'PluginMetadata',
    'PluginContributions',
    'ToolContribution',
    'ProviderContribution',
    'StoreContribution',
    'EventSinkContribution',
]


DEFAULT_PLUGIN_ENTRY_POINT_GROUP = "langgraph_automation.plugins"
_PLUGIN_DISCOVERY_COMPONENT = "plugin_discovery"


def discover_plugins(*, group: str = DEFAULT_PLUGIN_ENTRY_POINT_GROUP) -> tuple[Plugin, ...]:
    """Load optional installed plugins from Python entry points."""
    discovered: list[Plugin] = []
    entry_points = importlib_metadata.entry_points().select(group=group)
    for entry_point in sorted(entry_points, key=lambda item: (item.name, item.value)):
        try:
            loaded = entry_point.load()
            plugin = loaded() if callable(loaded) and not isinstance(loaded, Plugin) else loaded
        except Exception as exc:
            raise PluginResolutionError(
                f"Plugin discovery failed for entry point '{entry_point.name}'.",
                code="PLUGIN_DISCOVERY_FAILED",
                component=_PLUGIN_DISCOVERY_COMPONENT,
                metadata={"entry_point": entry_point.name, "group": group},
            ) from exc
        if not isinstance(plugin, Plugin):
            raise PluginResolutionError(
                f"Plugin discovery failed: entry point '{entry_point.name}' returned an invalid object.",
                code="PLUGIN_DISCOVERY_INVALID_RESULT",
                component=_PLUGIN_DISCOVERY_COMPONENT,
                metadata={"entry_point": entry_point.name, "group": group},
            )
        discovered.append(plugin)
    return tuple(discovered)


def _copy_mapping(mapping: Mapping[str, Any] | None) -> dict[str, Any]:
    return dict(mapping or {})


def _tupleize(values: object) -> tuple[object, ...]:
    if isinstance(values, tuple):
        return values
    return tuple(values)  # type: ignore[arg-type]


def _tupleize_strs(values: object) -> tuple[str, ...]:
    if isinstance(values, tuple):
        return values
    return tuple(values)  # type: ignore[arg-type]


def _tupleize_mapping_values(mapping: Mapping[str, object] | None) -> dict[str, tuple[str, ...]]:
    if not mapping:
        return {}
    return {key: _tupleize_strs(value) for key, value in mapping.items()}


@dataclass(frozen=True, slots=True)
class PluginMetadata:
    name: str
    version: str
    description: str = ''
    plugin_types: tuple[str, ...] = ()
    provides: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    requires: Mapping[str, str] = field(default_factory=dict)
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, 'plugin_types', _tupleize_strs(self.plugin_types))
        object.__setattr__(self, 'provides', _tupleize_mapping_values(self.provides))
        object.__setattr__(self, 'requires', dict(self.requires))
        object.__setattr__(self, 'metadata', _copy_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class ToolContribution:
    name: str
    description: str = ''
    capabilities: tuple[str, ...] = ()
    input_schema: Mapping[str, object] | None = None
    output_schema: Mapping[str, object] | None = None
    safety_metadata: Mapping[str, object] = field(default_factory=dict)
    validate_config: Callable[..., None] | None = None
    create_tool: Callable[..., object] | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, 'capabilities', _tupleize_strs(self.capabilities))
        object.__setattr__(self, 'input_schema', None if self.input_schema is None else dict(self.input_schema))
        object.__setattr__(self, 'output_schema', None if self.output_schema is None else dict(self.output_schema))
        object.__setattr__(self, 'safety_metadata', _copy_mapping(self.safety_metadata))
        object.__setattr__(self, 'metadata', _copy_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class ProviderContribution:
    name: str
    provider_type: str
    description: str = ''
    supported_parameters: tuple[str, ...] = ()
    default_parameters: Mapping[str, object] = field(default_factory=dict)
    validate_profile: Callable[..., None] | None = None
    create_client: Callable[..., object] | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, 'supported_parameters', _tupleize_strs(self.supported_parameters))
        object.__setattr__(self, 'default_parameters', _copy_mapping(self.default_parameters))
        object.__setattr__(self, 'metadata', _copy_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class StoreContribution:
    backend_name: str
    store_type: str
    description: str = ''
    validate_config: Callable[..., None] | None = None
    create_store: Callable[..., object] | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, 'metadata', _copy_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class EventSinkContribution:
    backend_name: str
    description: str = ''
    validate_config: Callable[..., None] | None = None
    create_sink: Callable[..., object] | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, 'metadata', _copy_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class PluginContributions:
    workflows: tuple[WorkflowContribution, ...] = ()
    tools: tuple[ToolContribution, ...] = ()
    providers: tuple[ProviderContribution, ...] = ()
    stores: tuple[StoreContribution, ...] = ()
    event_sinks: tuple[EventSinkContribution, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, 'workflows', tuple(self.workflows))
        object.__setattr__(self, 'tools', tuple(self.tools))
        object.__setattr__(self, 'providers', tuple(self.providers))
        object.__setattr__(self, 'stores', tuple(self.stores))
        object.__setattr__(self, 'event_sinks', tuple(self.event_sinks))


@dataclass(frozen=True, slots=True)
class Plugin:
    metadata: PluginMetadata
    contributions: PluginContributions = field(default_factory=PluginContributions)
