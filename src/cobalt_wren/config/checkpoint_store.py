"""Checkpoint store config normalization helpers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from cobalt_wren.api.errors import ConfigError

from .models import (
    CheckpointStoreSettings,
    FilesystemCheckpointStoreSettings,
    MemoryCheckpointStoreSettings,
    PostgresCheckpointStoreSettings,
    StoreBackendConfig,
)

__all__ = [
    "CheckpointStoreSettings",
    "FilesystemCheckpointStoreSettings",
    "MemoryCheckpointStoreSettings",
    "PostgresCheckpointStoreSettings",
    "normalize_checkpoint_store_settings",
]

_CONFIG_COMPONENT = "config_loader"


def normalize_checkpoint_store_settings(store_config: StoreBackendConfig | None) -> CheckpointStoreSettings:
    """Return typed checkpoint store settings for runtime composition."""

    if store_config is None:
        return MemoryCheckpointStoreSettings()

    backend = store_config.backend
    if backend == "memory":
        if store_config.config or store_config.metadata:
            raise _config_error(
                "Configuration is invalid: checkpoint store backend 'memory' does not accept extra options.",
                code="CONFIG_CHECKPOINT_STORE_MEMORY_OPTIONS",
                metadata={"backend": backend},
            )
        return MemoryCheckpointStoreSettings()

    if backend == "filesystem":
        if store_config.metadata:
            raise _config_error(
                "Configuration is invalid: checkpoint store backend 'filesystem' does not accept metadata.",
                code="CONFIG_CHECKPOINT_STORE_INVALID_METADATA",
                metadata={"backend": backend},
            )
        if set(store_config.config) != {"root"}:
            raise _config_error(
                "Configuration is invalid: filesystem checkpoint store requires exactly one root option.",
                code="CONFIG_CHECKPOINT_STORE_INVALID_OPTIONS",
                metadata={"backend": backend},
            )
        root = _normalize_root_value(store_config.config.get("root"))
        return FilesystemCheckpointStoreSettings(root=root)

    if backend == "postgres":
        allowed = {"dsn", "table_name"}
        dsn = store_config.config.get("dsn")
        if set(store_config.config) - allowed or not isinstance(dsn, str) or not dsn.strip():
            raise _config_error("Configuration is invalid: PostgreSQL checkpoint store requires a DSN and known options.", code="CONFIG_CHECKPOINT_STORE_INVALID_OPTIONS", metadata={"backend": backend})
        return PostgresCheckpointStoreSettings(dsn=dsn.strip(), table_name=str(store_config.config.get("table_name", "langgraph_automation_checkpoints")))

    raise _config_error(
        "Configuration is invalid: checkpoint store backend is not supported.",
        code="CONFIG_UNSUPPORTED_CHECKPOINT_STORE_BACKEND",
        metadata={"backend": backend},
    )


def _normalize_root_value(value: Any) -> Path:
    if not isinstance(value, (str, os.PathLike)):
        raise _config_error(
            "Configuration is invalid: filesystem checkpoint store root must be an absolute path.",
            code="CONFIG_CHECKPOINT_STORE_INVALID_ROOT",
        )
    try:
        raw = os.fspath(value)
    except TypeError:
        raise _config_error(
            "Configuration is invalid: filesystem checkpoint store root must be an absolute path.",
            code="CONFIG_CHECKPOINT_STORE_INVALID_ROOT",
        ) from None
    if not isinstance(raw, str) or not raw.strip():
        raise _config_error(
            "Configuration is invalid: filesystem checkpoint store root must be an absolute path.",
            code="CONFIG_CHECKPOINT_STORE_INVALID_ROOT",
        )

    candidate = raw.strip()
    if candidate.startswith("~") or "://" in candidate or "\x00" in candidate:
        raise _config_error(
            "Configuration is invalid: filesystem checkpoint store root must be an absolute path.",
            code="CONFIG_CHECKPOINT_STORE_INVALID_ROOT",
        )

    try:
        path = Path(candidate)
    except ValueError:
        raise _config_error(
            "Configuration is invalid: filesystem checkpoint store root must be an absolute path.",
            code="CONFIG_CHECKPOINT_STORE_INVALID_ROOT",
        ) from None
    if not path.is_absolute():
        raise _config_error(
            "Configuration is invalid: filesystem checkpoint store root must be an absolute path.",
            code="CONFIG_CHECKPOINT_STORE_INVALID_ROOT",
        )
    return path


def _config_error(
    safe_message: str,
    *,
    code: str,
    metadata: dict[str, Any] | None = None,
) -> ConfigError:
    return ConfigError(safe_message, code=code, component=_CONFIG_COMPONENT, metadata=metadata)
