"""Internal config models for package-level declarative config."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "EffectivePluginSet",
    "EventSinkBackendConfig",
    "LimitsConfig",
    "NormalizedPackageConfig",
    "PluginsConfig",
    "ProviderProfileConfig",
    "RawPackageConfig",
    "SafetyConfig",
    "SecretRef",
    "StoreBackendConfig",
    "ToolsConfig",
    "ValidatedPackageConfig",
]


def _copy_mapping(mapping: Mapping[str, Any] | None) -> dict[str, Any]:
    return dict(mapping or {})


def _tupleize_strings(values: object) -> tuple[str, ...]:
    if isinstance(values, tuple):
        return values
    return tuple(values)  # type: ignore[arg-type]


@dataclass(frozen=True, slots=True)
class SecretRef:
    """Reference to a secret value that is resolved later."""

    source: str
    name: str

    def __post_init__(self) -> None:
        if self.source != "env":
            raise ValueError("secret references must use source='env'")
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("secret reference name must not be empty")


@dataclass(frozen=True, slots=True)
class RawPackageConfig:
    """Source-facing package config before normalization."""

    version: int
    environment: str | None = None
    plugins: Mapping[str, Any] = field(default_factory=dict)
    providers: Mapping[str, Any] = field(default_factory=dict)
    tools: Mapping[str, Any] = field(default_factory=dict)
    stores: Mapping[str, Any] = field(default_factory=dict)
    event_sinks: Mapping[str, Any] = field(default_factory=dict)
    limits: Mapping[str, Any] = field(default_factory=dict)
    observability: Mapping[str, Any] = field(default_factory=dict)
    safety: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "plugins", _copy_mapping(self.plugins))
        object.__setattr__(self, "providers", _copy_mapping(self.providers))
        object.__setattr__(self, "tools", _copy_mapping(self.tools))
        object.__setattr__(self, "stores", _copy_mapping(self.stores))
        object.__setattr__(self, "event_sinks", _copy_mapping(self.event_sinks))
        object.__setattr__(self, "limits", _copy_mapping(self.limits))
        object.__setattr__(self, "observability", _copy_mapping(self.observability))
        object.__setattr__(self, "safety", _copy_mapping(self.safety))
        object.__setattr__(self, "metadata", _copy_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class PluginsConfig:
    enabled: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "enabled", _tupleize_strings(self.enabled))


@dataclass(frozen=True, slots=True)
class ToolsConfig:
    allowlist: tuple[str, ...] = ()
    configs: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "allowlist", _tupleize_strings(self.allowlist))
        object.__setattr__(self, "configs", _copy_mapping(self.configs))


@dataclass(frozen=True, slots=True)
class SafetyConfig:
    redaction_enabled: bool = True
    safe_errors: bool = True


@dataclass(frozen=True, slots=True)
class LimitsConfig:
    values: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "values", _copy_mapping(self.values))


@dataclass(frozen=True, slots=True)
class ProviderProfileConfig:
    provider: str
    model: str | None = None
    parameters: Mapping[str, Any] = field(default_factory=dict)
    secrets: Mapping[str, SecretRef] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "parameters", _copy_mapping(self.parameters))
        object.__setattr__(self, "secrets", _copy_mapping(self.secrets))
        object.__setattr__(self, "metadata", _copy_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class StoreBackendConfig:
    backend: str
    config: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "config", _copy_mapping(self.config))
        object.__setattr__(self, "metadata", _copy_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class EventSinkBackendConfig:
    backend: str
    config: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "config", _copy_mapping(self.config))
        object.__setattr__(self, "metadata", _copy_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class NormalizedPackageConfig:
    """Normalized package-level config with defaults applied."""

    version: int
    environment: str
    plugins: PluginsConfig
    providers: Mapping[str, ProviderProfileConfig]
    tools: ToolsConfig
    stores: Mapping[str, StoreBackendConfig]
    event_sinks: Mapping[str, EventSinkBackendConfig]
    limits: LimitsConfig
    observability: Mapping[str, Any]
    safety: SafetyConfig
    metadata: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "providers", _copy_mapping(self.providers))
        object.__setattr__(self, "stores", _copy_mapping(self.stores))
        object.__setattr__(self, "event_sinks", _copy_mapping(self.event_sinks))
        object.__setattr__(self, "observability", _copy_mapping(self.observability))
        object.__setattr__(self, "metadata", _copy_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class EffectivePluginSet:
    plugins: tuple[object, ...]
    plugin_names: tuple[str, ...]
    tools: Mapping[str, object]
    providers: Mapping[str, object]
    stores: Mapping[tuple[str, str], object]
    event_sinks: Mapping[str, object]

    def __post_init__(self) -> None:
        object.__setattr__(self, "plugins", tuple(self.plugins))
        object.__setattr__(self, "plugin_names", _tupleize_strings(self.plugin_names))
        object.__setattr__(self, "tools", _copy_mapping(self.tools))
        object.__setattr__(self, "providers", _copy_mapping(self.providers))
        object.__setattr__(self, "stores", _copy_mapping(self.stores))
        object.__setattr__(self, "event_sinks", _copy_mapping(self.event_sinks))


@dataclass(frozen=True, slots=True)
class ValidatedPackageConfig:
    normalized: NormalizedPackageConfig
    effective_plugins: EffectivePluginSet
