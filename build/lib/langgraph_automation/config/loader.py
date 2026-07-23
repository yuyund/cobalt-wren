"""Load raw package config from mapping input."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from langgraph_automation.api.errors import ConfigError

from .models import RawPackageConfig
from .security import precheck_package_config_mapping

SUPPORTED_VERSION = 1
_CONFIG_COMPONENT = "config_loader"
_KNOWN_TOP_LEVEL_FIELDS = {
    "event_sinks",
    "environment",
    "limits",
    "metadata",
    "observability",
    "plugins",
    "providers",
    "safety",
    "stores",
    "tools",
    "version",
}


def load_package_config_from_mapping(data: Mapping[str, object]) -> RawPackageConfig:
    """Load a raw config model from a mapping."""

    if not isinstance(data, Mapping):
        raise _config_error(
            "Configuration is invalid: package config must be a mapping.",
            code="CONFIG_INVALID_MAPPING",
        )

    version = data.get("version")
    if version is None:
        raise _config_error("Configuration is invalid: version is required.", code="CONFIG_MISSING_VERSION")
    if not isinstance(version, int) or isinstance(version, bool):
        raise _config_error(
            "Configuration is invalid: version must be an integer.",
            code="CONFIG_INVALID_VERSION_TYPE",
        )
    if version != SUPPORTED_VERSION:
        raise _config_error(
            f"Configuration is invalid: version {version} is not supported.",
            code="CONFIG_UNSUPPORTED_VERSION",
            metadata={"supported_version": SUPPORTED_VERSION},
        )

    unknown_fields = sorted(set(data) - _KNOWN_TOP_LEVEL_FIELDS)
    if unknown_fields:
        raise _config_error(
            f"Configuration is invalid: unknown top-level field '{unknown_fields[0]}'.",
            code="CONFIG_UNKNOWN_TOP_LEVEL_FIELD",
            metadata={"field_name": unknown_fields[0]},
        )

    precheck_package_config_mapping(data)

    return RawPackageConfig(
        version=version,
        environment=_string_or_none(data.get("environment")),
        plugins=_mapping_or_empty(data.get("plugins"), field_name="plugins"),
        providers=_mapping_or_empty(data.get("providers"), field_name="providers"),
        tools=_mapping_or_empty(data.get("tools"), field_name="tools"),
        stores=_mapping_or_empty(data.get("stores"), field_name="stores"),
        event_sinks=_mapping_or_empty(data.get("event_sinks"), field_name="event_sinks"),
        limits=_mapping_or_empty(data.get("limits"), field_name="limits"),
        observability=_mapping_or_empty(data.get("observability"), field_name="observability"),
        safety=_mapping_or_empty(data.get("safety"), field_name="safety"),
        metadata=_mapping_or_empty(data.get("metadata"), field_name="metadata"),
    )


def _mapping_or_empty(value: object, *, field_name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise _config_error(
            f"Configuration is invalid: {field_name} must be a mapping.",
            code="CONFIG_INVALID_FIELD_TYPE",
            metadata={"field_name": field_name},
        )
    return dict(value)


def _string_or_none(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise _config_error(
            "Configuration is invalid: environment must be a string.",
            code="CONFIG_INVALID_FIELD_TYPE",
            metadata={"field_name": "environment"},
        )
    environment = value.strip()
    if not environment:
        raise _config_error(
            "Configuration is invalid: environment must not be empty.",
            code="CONFIG_INVALID_FIELD_TYPE",
            metadata={"field_name": "environment"},
        )
    return environment


def _config_error(
    safe_message: str,
    *,
    code: str,
    metadata: dict[str, Any] | None = None,
) -> ConfigError:
    return ConfigError(safe_message, code=code, component=_CONFIG_COMPONENT, metadata=metadata)
