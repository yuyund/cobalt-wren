"""Normalize raw package config into internal typed config models."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from langgraph_automation.api.errors import ConfigError

from .loader import SUPPORTED_VERSION, load_package_config_from_mapping
from .artifact_store import normalize_artifact_store_settings
from .checkpoint_store import normalize_checkpoint_store_settings
from .models import (
    EventSinkBackendConfig,
    LimitsConfig,
    NormalizedPackageConfig,
    PluginsConfig,
    ProviderProfileConfig,
    RawPackageConfig,
    SafetyConfig,
    SecretRef,
    StoreBackendConfig,
    ToolsConfig,
)
from .security import normalize_secret_reference, precheck_package_config_mapping

_CONFIG_COMPONENT = "config_loader"


def load_normalized_package_config_from_mapping(data: Mapping[str, object]) -> NormalizedPackageConfig:
    """Convenience helper that loads and normalizes package config."""

    return normalize_package_config(load_package_config_from_mapping(data))


def normalize_package_config(raw: RawPackageConfig) -> NormalizedPackageConfig:
    """Normalize a raw config model into typed config."""

    if not isinstance(raw, RawPackageConfig):
        raise TypeError("raw must be a RawPackageConfig")
    if raw.version != SUPPORTED_VERSION:
        raise _config_error(
            f"Configuration is invalid: version {raw.version} is not supported.",
            code="CONFIG_UNSUPPORTED_VERSION",
            metadata={"supported_version": SUPPORTED_VERSION},
        )

    precheck_package_config_mapping(_raw_config_as_mapping(raw))

    plugins = _normalize_plugins(raw.plugins)
    tools = _normalize_tools(raw.tools)
    providers = _normalize_providers(raw.providers)
    stores = _normalize_store_backends(raw.stores)
    normalize_artifact_store_settings(stores.get("artifact"))
    event_sinks = _normalize_event_sinks(raw.event_sinks)
    safety = _normalize_safety(raw.safety)
    checkpoint_store = normalize_checkpoint_store_settings(stores.get("checkpoint"))

    return NormalizedPackageConfig(
        version=raw.version,
        environment=_normalize_environment(raw.environment),
        plugins=plugins,
        providers=providers,
        tools=tools,
        stores=stores,
        event_sinks=event_sinks,
        limits=LimitsConfig(values=dict(raw.limits)),
        observability=dict(raw.observability),
        safety=safety,
        metadata=dict(raw.metadata),
        checkpoint_store=checkpoint_store,
    )


def _raw_config_as_mapping(raw: RawPackageConfig) -> dict[str, object]:
    return {
        "version": raw.version,
        "environment": raw.environment,
        "plugins": dict(raw.plugins),
        "providers": dict(raw.providers),
        "tools": dict(raw.tools),
        "stores": dict(raw.stores),
        "event_sinks": dict(raw.event_sinks),
        "limits": dict(raw.limits),
        "observability": dict(raw.observability),
        "safety": dict(raw.safety),
        "metadata": dict(raw.metadata),
    }


def _normalize_environment(environment: str | None) -> str:
    if environment is None:
        return "default"
    if not isinstance(environment, str):
        raise _config_error(
            "Configuration is invalid: environment must be a string.",
            code="CONFIG_INVALID_FIELD_TYPE",
            metadata={"field_name": "environment"},
        )
    normalized = environment.strip()
    if not normalized:
        raise _config_error(
            "Configuration is invalid: environment must not be empty.",
            code="CONFIG_INVALID_FIELD_TYPE",
            metadata={"field_name": "environment"},
        )
    return normalized


def _normalize_plugins(raw_plugins: Mapping[str, Any]) -> PluginsConfig:
    if not isinstance(raw_plugins, Mapping):
        raise _config_error("Configuration is invalid: plugins must be a mapping.", code="CONFIG_INVALID_FIELD_TYPE")
    allowed_fields = {"enabled"}
    unknown_fields = sorted(set(raw_plugins) - allowed_fields)
    if unknown_fields:
        raise _config_error(
            f"Configuration is invalid: unknown plugins field '{unknown_fields[0]}'.",
            code="CONFIG_UNKNOWN_TOP_LEVEL_FIELD",
            metadata={"field_name": f"plugins.{unknown_fields[0]}"},
        )

    enabled = _normalize_unique_string_sequence(
        raw_plugins.get("enabled", ()),
        field_name="plugins.enabled",
        duplicate_code="CONFIG_DUPLICATE_ENABLED_PLUGIN",
    )
    return PluginsConfig(enabled=enabled)


def _normalize_tools(raw_tools: Mapping[str, Any]) -> ToolsConfig:
    if not isinstance(raw_tools, Mapping):
        raise _config_error("Configuration is invalid: tools must be a mapping.", code="CONFIG_INVALID_FIELD_TYPE")
    allowed_fields = {"allowlist", "configs"}
    unknown_fields = sorted(set(raw_tools) - allowed_fields)
    if unknown_fields:
        raise _config_error(
            f"Configuration is invalid: unknown tools field '{unknown_fields[0]}'.",
            code="CONFIG_UNKNOWN_TOP_LEVEL_FIELD",
            metadata={"field_name": f"tools.{unknown_fields[0]}"},
        )

    allowlist = _normalize_unique_string_sequence(
        raw_tools.get("allowlist", ()),
        field_name="tools.allowlist",
        duplicate_code="CONFIG_DUPLICATE_TOOL_ALLOWLIST",
    )
    configs = raw_tools.get("configs", {})
    if configs is None:
        configs = {}
    if not isinstance(configs, Mapping):
        raise _config_error(
            "Configuration is invalid: tools.configs must be a mapping.",
            code="CONFIG_INVALID_FIELD_TYPE",
            metadata={"field_name": "tools.configs"},
        )
    return ToolsConfig(allowlist=allowlist, configs={key: _copy_value(value) for key, value in configs.items()})


def _normalize_providers(raw_providers: Mapping[str, Any]) -> dict[str, ProviderProfileConfig]:
    if not isinstance(raw_providers, Mapping):
        raise _config_error("Configuration is invalid: providers must be a mapping.", code="CONFIG_INVALID_FIELD_TYPE")

    normalized: dict[str, ProviderProfileConfig] = {}
    for profile_name, profile_value in raw_providers.items():
        if not isinstance(profile_name, str) or not profile_name:
            raise _config_error(
                "Configuration is invalid: provider profile names must be non-empty strings.",
                code="CONFIG_INVALID_FIELD_TYPE",
                metadata={"field_name": "providers"},
            )
        if not isinstance(profile_value, Mapping):
            raise _config_error(
                f"Configuration is invalid: provider profile '{profile_name}' must be a mapping.",
                code="CONFIG_INVALID_FIELD_TYPE",
                metadata={"profile_name": profile_name},
            )

        normalized[profile_name] = _normalize_provider_profile(profile_name, profile_value)
    return normalized


def _normalize_provider_profile(profile_name: str, profile_value: Mapping[str, Any]) -> ProviderProfileConfig:
    provider = profile_value.get("provider")
    if not isinstance(provider, str) or not provider.strip():
        raise _config_error(
            f"Configuration is invalid: provider profile '{profile_name}' must name a provider.",
            code="CONFIG_INVALID_FIELD_TYPE",
            metadata={"profile_name": profile_name},
        )

    model_value = profile_value.get("model")
    model = None
    if model_value is not None:
        if not isinstance(model_value, str):
            raise _config_error(
                f"Configuration is invalid: provider profile '{profile_name}' model must be a string.",
                code="CONFIG_INVALID_FIELD_TYPE",
                metadata={"profile_name": profile_name},
            )
        model = model_value.strip() or None

    metadata = profile_value.get("metadata", {})
    if metadata is None:
        metadata = {}
    if not isinstance(metadata, Mapping):
        raise _config_error(
            f"Configuration is invalid: provider profile '{profile_name}' metadata must be a mapping.",
            code="CONFIG_INVALID_FIELD_TYPE",
            metadata={"profile_name": profile_name},
        )

    secrets = _normalize_provider_secrets(profile_name, profile_value)
    parameters = _normalize_provider_parameters(profile_value)
    return ProviderProfileConfig(
        provider=provider.strip(),
        model=model,
        parameters=parameters,
        secrets=secrets,
        metadata=dict(metadata),
    )


def _normalize_provider_parameters(profile_value: Mapping[str, Any]) -> dict[str, Any]:
    parameters = profile_value.get("parameters", {})
    if parameters is None:
        parameters = {}
    if not isinstance(parameters, Mapping):
        raise _config_error(
            "Configuration is invalid: provider parameters must be a mapping.",
            code="CONFIG_INVALID_FIELD_TYPE",
            metadata={"field_name": "providers.parameters"},
        )

    ignored_fields = {"provider", "model", "parameters", "secrets", "metadata"}
    normalized: dict[str, Any] = {key: _copy_value(value) for key, value in parameters.items()}
    for key, value in profile_value.items():
        if key in ignored_fields or key.endswith("_env"):
            continue
        normalized.setdefault(key, _copy_value(value))
    return normalized


def _normalize_provider_secrets(profile_name: str, profile_value: Mapping[str, Any]) -> dict[str, SecretRef]:
    secrets: dict[str, SecretRef] = {}

    explicit = profile_value.get("secrets", {})
    if explicit is None:
        explicit = {}
    if not isinstance(explicit, Mapping):
        raise _config_error(
            f"Configuration is invalid: provider profile '{profile_name}' secrets must be a mapping.",
            code="CONFIG_INVALID_FIELD_TYPE",
            metadata={"profile_name": profile_name},
        )

    for secret_name, secret_value in explicit.items():
        if not isinstance(secret_name, str) or not secret_name:
            raise _config_error(
                f"Configuration is invalid: provider profile '{profile_name}' secret names must be strings.",
                code="CONFIG_INVALID_FIELD_TYPE",
                metadata={"profile_name": profile_name},
            )
        if secret_name in secrets:
            raise _config_error(
                f"Configuration is invalid: duplicate secret reference '{secret_name}'.",
                code="CONFIG_DUPLICATE_SECRET_REFERENCE",
                metadata={"profile_name": profile_name, "secret_name": secret_name},
            )
        secrets[secret_name] = _normalize_secret_ref(secret_name, secret_value)

    for key, value in profile_value.items():
        if not key.endswith("_env"):
            continue
        secret_name = key[:-4]
        if secret_name in secrets:
            raise _config_error(
                f"Configuration is invalid: duplicate secret reference '{secret_name}'.",
                code="CONFIG_DUPLICATE_SECRET_REFERENCE",
                metadata={"profile_name": profile_name, "secret_name": secret_name},
            )
        env_name = normalize_secret_reference(value, field_name=f"providers.{profile_name}.{key}")
        secrets[secret_name] = SecretRef(source="env", name=env_name)

    return secrets


def _normalize_secret_ref(secret_name: str, secret_value: Any) -> SecretRef:
    if isinstance(secret_value, str):
        env_name = normalize_secret_reference(secret_value, field_name=f"secrets.{secret_name}")
        return SecretRef(source="env", name=env_name)
    if isinstance(secret_value, Mapping):
        source = secret_value.get("source")
        name = secret_value.get("name")
        if source != "env" or not isinstance(name, str):
            raise _config_error(
                "Configuration is invalid: secret references must use source='env'.",
                code="CONFIG_SECRET_LITERAL",
                metadata={"secret_name": secret_name},
            )
        return SecretRef(source="env", name=normalize_secret_reference(name, field_name=f"secrets.{secret_name}.name"))
    raise _config_error(
        "Configuration is invalid: secret references must be strings or env mappings.",
        code="CONFIG_SECRET_LITERAL",
        metadata={"secret_name": secret_name},
    )


def _normalize_store_backends(raw_stores: Mapping[str, Any]) -> dict[str, StoreBackendConfig]:
    if not isinstance(raw_stores, Mapping):
        raise _config_error("Configuration is invalid: stores must be a mapping.", code="CONFIG_INVALID_FIELD_TYPE")

    normalized: dict[str, StoreBackendConfig] = {}
    for store_type, store_value in raw_stores.items():
        if not isinstance(store_type, str) or not store_type:
            raise _config_error(
                "Configuration is invalid: store types must be non-empty strings.",
                code="CONFIG_INVALID_FIELD_TYPE",
                metadata={"field_name": "stores"},
            )
        if not isinstance(store_value, Mapping):
            raise _config_error(
                f"Configuration is invalid: store '{store_type}' must be a mapping.",
                code="CONFIG_INVALID_FIELD_TYPE",
                metadata={"store_type": store_type},
            )
        backend = store_value.get("backend")
        if not isinstance(backend, str) or not backend.strip():
            raise _config_error(
                f"Configuration is invalid: store '{store_type}' must name a backend.",
                code="CONFIG_INVALID_FIELD_TYPE",
                metadata={"store_type": store_type},
            )
        config = store_value.get("config", {})
        if config is None:
            config = {}
        if not isinstance(config, Mapping):
            raise _config_error(
                f"Configuration is invalid: store '{store_type}' config must be a mapping.",
                code="CONFIG_INVALID_FIELD_TYPE",
                metadata={"store_type": store_type},
            )
        metadata = store_value.get("metadata", {})
        if metadata is None:
            metadata = {}
        if not isinstance(metadata, Mapping):
            raise _config_error(
                f"Configuration is invalid: store '{store_type}' metadata must be a mapping.",
                code="CONFIG_INVALID_FIELD_TYPE",
                metadata={"store_type": store_type},
            )
        merged_config = {key: _copy_value(value) for key, value in config.items()}
        for key, value in store_value.items():
            if key in {"backend", "config", "metadata"}:
                continue
            merged_config.setdefault(key, _copy_value(value))
        normalized[store_type] = StoreBackendConfig(
            backend=backend.strip(),
            config=merged_config,
            metadata=dict(metadata),
        )
    return normalized


def _normalize_event_sinks(raw_event_sinks: Mapping[str, Any]) -> dict[str, EventSinkBackendConfig]:
    if not isinstance(raw_event_sinks, Mapping):
        raise _config_error(
            "Configuration is invalid: event_sinks must be a mapping.",
            code="CONFIG_INVALID_FIELD_TYPE",
        )

    normalized: dict[str, EventSinkBackendConfig] = {}
    for sink_name, sink_value in raw_event_sinks.items():
        if not isinstance(sink_name, str) or not sink_name:
            raise _config_error(
                "Configuration is invalid: event sink names must be non-empty strings.",
                code="CONFIG_INVALID_FIELD_TYPE",
                metadata={"field_name": "event_sinks"},
            )
        if not isinstance(sink_value, Mapping):
            raise _config_error(
                f"Configuration is invalid: event sink '{sink_name}' must be a mapping.",
                code="CONFIG_INVALID_FIELD_TYPE",
                metadata={"sink_name": sink_name},
            )
        backend = sink_value.get("backend")
        if not isinstance(backend, str) or not backend.strip():
            raise _config_error(
                f"Configuration is invalid: event sink '{sink_name}' must name a backend.",
                code="CONFIG_INVALID_FIELD_TYPE",
                metadata={"sink_name": sink_name},
            )
        config = sink_value.get("config", {})
        if config is None:
            config = {}
        if not isinstance(config, Mapping):
            raise _config_error(
                f"Configuration is invalid: event sink '{sink_name}' config must be a mapping.",
                code="CONFIG_INVALID_FIELD_TYPE",
                metadata={"sink_name": sink_name},
            )
        metadata = sink_value.get("metadata", {})
        if metadata is None:
            metadata = {}
        if not isinstance(metadata, Mapping):
            raise _config_error(
                f"Configuration is invalid: event sink '{sink_name}' metadata must be a mapping.",
                code="CONFIG_INVALID_FIELD_TYPE",
                metadata={"sink_name": sink_name},
            )
        merged_config = {key: _copy_value(value) for key, value in config.items()}
        for key, value in sink_value.items():
            if key in {"backend", "config", "metadata"}:
                continue
            merged_config.setdefault(key, _copy_value(value))
        normalized[sink_name] = EventSinkBackendConfig(
            backend=backend.strip(),
            config=merged_config,
            metadata=dict(metadata),
        )
    return normalized


def _normalize_safety(raw_safety: Mapping[str, Any]) -> SafetyConfig:
    if not isinstance(raw_safety, Mapping):
        raise _config_error("Configuration is invalid: safety must be a mapping.", code="CONFIG_INVALID_FIELD_TYPE")
    if raw_safety.get("enabled") is False:
        _raise_safety_error("safety")
    if raw_safety.get("redaction_enabled") is False:
        _raise_safety_error("redaction")
    if raw_safety.get("safe_errors") is False:
        _raise_safety_error("safe errors")
    return SafetyConfig(redaction_enabled=True, safe_errors=True)


def _normalize_unique_string_sequence(value: object, *, field_name: str, duplicate_code: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        raise _config_error(
            f"Configuration is invalid: {field_name} must be a sequence of strings.",
            code="CONFIG_INVALID_FIELD_TYPE",
            metadata={"field_name": field_name},
        )
    if not isinstance(value, (list, tuple)):
        raise _config_error(
            f"Configuration is invalid: {field_name} must be a sequence of strings.",
            code="CONFIG_INVALID_FIELD_TYPE",
            metadata={"field_name": field_name},
        )

    seen: set[str] = set()
    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise _config_error(
                f"Configuration is invalid: {field_name} entries must be strings.",
                code="CONFIG_INVALID_FIELD_TYPE",
                metadata={"field_name": field_name},
            )
        name = item.strip()
        if not name:
            raise _config_error(
                f"Configuration is invalid: {field_name} entries must not be empty.",
                code="CONFIG_INVALID_FIELD_TYPE",
                metadata={"field_name": field_name},
            )
        if name in seen:
            raise _config_error(
                f"Configuration is invalid: duplicate entry '{name}' in {field_name}.",
                code=duplicate_code,
                metadata={"field_name": field_name, "entry": name},
            )
        seen.add(name)
        normalized.append(name)
    return tuple(normalized)


def _copy_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, list):
        return [_copy_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_copy_value(item) for item in value)
    return value


def _raise_safety_error(kind: str) -> None:
    raise _config_error(
        f"Configuration is invalid: {kind} cannot be disabled.",
        code="CONFIG_SAFETY_DISABLED",
    )


def _config_error(
    safe_message: str,
    *,
    code: str,
    metadata: dict[str, Any] | None = None,
) -> ConfigError:
    return ConfigError(safe_message, code=code, component=_CONFIG_COMPONENT, metadata=metadata)
