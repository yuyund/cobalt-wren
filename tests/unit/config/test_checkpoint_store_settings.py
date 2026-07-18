from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from langgraph_automation.api.errors import ConfigError
from langgraph_automation.config.models import (
    FilesystemCheckpointStoreSettings,
    MemoryCheckpointStoreSettings,
)
from langgraph_automation.config.normalizer import load_normalized_package_config_from_mapping


def test_checkpoint_store_settings_default_to_memory_when_section_is_absent() -> None:
    normalized = load_normalized_package_config_from_mapping({"version": 1})

    assert normalized.checkpoint_store == MemoryCheckpointStoreSettings()
    assert normalized.checkpoint_store.backend == "memory"


def test_checkpoint_store_settings_accept_explicit_memory_backend() -> None:
    normalized = load_normalized_package_config_from_mapping(
        {
            "version": 1,
            "stores": {
                "checkpoint": {
                    "backend": "memory",
                }
            },
        }
    )

    assert normalized.checkpoint_store == MemoryCheckpointStoreSettings()


def test_checkpoint_store_settings_accept_explicit_filesystem_backend(tmp_path: Path) -> None:
    root = tmp_path / "checkpoints"
    normalized = load_normalized_package_config_from_mapping(
        {
            "version": 1,
            "stores": {
                "checkpoint": {
                    "backend": "filesystem",
                    "config": {
                        "root": str(root),
                    },
                }
            },
        }
    )

    assert normalized.checkpoint_store == FilesystemCheckpointStoreSettings(root=root)
    assert normalized.checkpoint_store.root == root
    assert str(root) not in repr(normalized.checkpoint_store)


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        ({"version": 1, "stores": {"checkpoint": {}}}, "CONFIG_INVALID_FIELD_TYPE"),
        ({"version": 1, "stores": {"checkpoint": None}}, "CONFIG_INVALID_FIELD_TYPE"),
        ({"version": 1, "stores": {"checkpoint": {"backend": "filesystem"}}}, "CONFIG_CHECKPOINT_STORE_INVALID_OPTIONS"),
        ({"version": 1, "stores": {"checkpoint": {"backend": "filesystem", "config": {}}}}, "CONFIG_CHECKPOINT_STORE_INVALID_OPTIONS"),
        ({"version": 1, "stores": {"checkpoint": {"backend": "filesystem", "config": {"root": "checkpoints"}}}}, "CONFIG_CHECKPOINT_STORE_INVALID_ROOT"),
        ({"version": 1, "stores": {"checkpoint": {"backend": "filesystem", "config": {"root": "/tmp/checkpoints", "extra": True}}}}, "CONFIG_CHECKPOINT_STORE_INVALID_OPTIONS"),
        ({"version": 1, "stores": {"checkpoint": {"backend": "memory", "config": {"root": "/tmp/checkpoints"}}}}, "CONFIG_CHECKPOINT_STORE_MEMORY_OPTIONS"),
        ({"version": 1, "stores": {"checkpoint": {"backend": "sqlite"}}}, "CONFIG_UNSUPPORTED_CHECKPOINT_STORE_BACKEND"),
    ],
)
def test_checkpoint_store_settings_reject_invalid_payloads(payload: dict[str, object], code: str) -> None:
    with pytest.raises(ConfigError) as excinfo:
        load_normalized_package_config_from_mapping(payload)

    assert excinfo.value.code == code


def test_checkpoint_store_settings_are_frozen() -> None:
    settings = MemoryCheckpointStoreSettings()

    with pytest.raises(FrozenInstanceError):
        settings.backend = "filesystem"  # type: ignore[misc]
