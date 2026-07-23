"""Artifact store config normalization helpers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from langgraph_automation.api.errors import ConfigError

from .models import ArtifactStoreSettings, FilesystemArtifactStoreSettings, MemoryArtifactStoreSettings, S3ArtifactStoreSettings, StoreBackendConfig

__all__ = [
    "ArtifactStoreSettings",
    "FilesystemArtifactStoreSettings",
    "MemoryArtifactStoreSettings",
    "S3ArtifactStoreSettings",
    "normalize_artifact_store_settings",
]

_CONFIG_COMPONENT = "config_loader"


def normalize_artifact_store_settings(store_config: StoreBackendConfig | None) -> ArtifactStoreSettings:
    """Return the typed artifact store settings for runtime composition."""

    if store_config is None:
        return MemoryArtifactStoreSettings()

    backend = store_config.backend
    if backend == "memory":
        if store_config.config or store_config.metadata:
            raise _config_error(
                "Configuration is invalid: artifact store backend 'memory' does not accept extra options.",
                code="CONFIG_ARTIFACT_STORE_MEMORY_OPTIONS",
                metadata={"backend": backend},
            )
        return MemoryArtifactStoreSettings()

    if backend == "filesystem":
        if store_config.metadata:
            raise _config_error(
                "Configuration is invalid: artifact store backend 'filesystem' does not accept metadata.",
                code="CONFIG_ARTIFACT_STORE_INVALID_METADATA",
                metadata={"backend": backend},
            )
        if set(store_config.config) != {"root"}:
            raise _config_error(
                "Configuration is invalid: filesystem artifact store requires exactly one root option.",
                code="CONFIG_ARTIFACT_STORE_INVALID_OPTIONS",
                metadata={"backend": backend},
            )
        root = _normalize_root_value(store_config.config.get("root"))
        return FilesystemArtifactStoreSettings(root=root)

    if backend == "s3":
        allowed = {"bucket", "prefix", "endpoint_url", "region_name"}
        if set(store_config.config) - allowed or not isinstance(store_config.config.get("bucket"), str) or not store_config.config.get("bucket", "").strip():
            raise _config_error("Configuration is invalid: S3 artifact store requires a bucket and known options.", code="CONFIG_ARTIFACT_STORE_INVALID_OPTIONS", metadata={"backend": backend})
        return S3ArtifactStoreSettings(bucket=store_config.config["bucket"].strip(), prefix=str(store_config.config.get("prefix", "")), endpoint_url=store_config.config.get("endpoint_url"), region_name=store_config.config.get("region_name"))

    raise _config_error(
        "Configuration is invalid: artifact store backend is not supported.",
        code="CONFIG_UNSUPPORTED_ARTIFACT_STORE_BACKEND",
        metadata={"backend": backend},
    )


def _normalize_root_value(value: Any) -> Path:
    if not isinstance(value, (str, os.PathLike)):
        raise _config_error(
            "Configuration is invalid: filesystem artifact store root must be an absolute path.",
            code="CONFIG_ARTIFACT_STORE_INVALID_ROOT",
        )
    try:
        raw = os.fspath(value)
    except TypeError:
        raise _config_error(
            "Configuration is invalid: filesystem artifact store root must be an absolute path.",
            code="CONFIG_ARTIFACT_STORE_INVALID_ROOT",
        ) from None
    if not isinstance(raw, str) or not raw.strip():
        raise _config_error(
            "Configuration is invalid: filesystem artifact store root must be an absolute path.",
            code="CONFIG_ARTIFACT_STORE_INVALID_ROOT",
        )

    candidate = raw.strip()
    if candidate.startswith("~") or "://" in candidate or "\x00" in candidate:
        raise _config_error(
            "Configuration is invalid: filesystem artifact store root must be an absolute path.",
            code="CONFIG_ARTIFACT_STORE_INVALID_ROOT",
        )

    try:
        path = Path(candidate)
    except ValueError:
        raise _config_error(
            "Configuration is invalid: filesystem artifact store root must be an absolute path.",
            code="CONFIG_ARTIFACT_STORE_INVALID_ROOT",
        ) from None
    if not path.is_absolute():
        raise _config_error(
            "Configuration is invalid: filesystem artifact store root must be an absolute path.",
            code="CONFIG_ARTIFACT_STORE_INVALID_ROOT",
        )
    return path


def _config_error(
    safe_message: str,
    *,
    code: str,
    metadata: dict[str, Any] | None = None,
) -> ConfigError:
    return ConfigError(safe_message, code=code, component=_CONFIG_COMPONENT, metadata=metadata)
