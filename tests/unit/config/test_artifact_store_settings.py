from __future__ import annotations

from pathlib import Path

import pytest

from cobalt_wren.api.errors import ConfigError
from cobalt_wren.config.artifact_store import (
    FilesystemArtifactStoreSettings,
    MemoryArtifactStoreSettings,
    normalize_artifact_store_settings,
)
from cobalt_wren.config.models import StoreBackendConfig


def test_normalize_artifact_store_settings_defaults_to_memory_when_section_is_absent() -> None:
    settings = normalize_artifact_store_settings(None)

    assert settings == MemoryArtifactStoreSettings()


def test_normalize_artifact_store_settings_accepts_explicit_memory() -> None:
    settings = normalize_artifact_store_settings(StoreBackendConfig(backend="memory"))

    assert settings == MemoryArtifactStoreSettings()


def test_normalize_artifact_store_settings_accepts_filesystem_root() -> None:
    settings = normalize_artifact_store_settings(
        StoreBackendConfig(backend="filesystem", config={"root": "/srv/cobalt-wren/artifacts"})
    )

    assert settings == FilesystemArtifactStoreSettings(root=Path("/srv/cobalt-wren/artifacts"))
    assert "/srv/cobalt-wren/artifacts" not in repr(settings)


@pytest.mark.parametrize(
    ("store_config", "code"),
    [
        (StoreBackendConfig(backend="filesystem"), "CONFIG_ARTIFACT_STORE_INVALID_OPTIONS"),
        (StoreBackendConfig(backend="filesystem", config={"root": "./artifacts"}), "CONFIG_ARTIFACT_STORE_INVALID_ROOT"),
        (StoreBackendConfig(backend="filesystem", config={"root": "~/artifacts"}), "CONFIG_ARTIFACT_STORE_INVALID_ROOT"),
        (StoreBackendConfig(backend="filesystem", config={"root": "file:///srv/artifacts"}), "CONFIG_ARTIFACT_STORE_INVALID_ROOT"),
        (StoreBackendConfig(backend="filesystem", config={"root": ""}), "CONFIG_ARTIFACT_STORE_INVALID_ROOT"),
        (StoreBackendConfig(backend="memory", config={"root": "/srv/cobalt-wren/artifacts"}), "CONFIG_ARTIFACT_STORE_MEMORY_OPTIONS"),
        (StoreBackendConfig(backend="sqlite"), "CONFIG_UNSUPPORTED_ARTIFACT_STORE_BACKEND"),
    ],
)
def test_normalize_artifact_store_settings_rejects_invalid_config(store_config: StoreBackendConfig, code: str) -> None:
    with pytest.raises(ConfigError) as excinfo:
        normalize_artifact_store_settings(store_config)

    assert excinfo.value.code == code
    assert "/srv/cobalt-wren/artifacts" not in str(excinfo.value)
