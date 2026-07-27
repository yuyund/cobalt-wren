"""Canonical checkpoint store composition for runtime assembly."""

from __future__ import annotations

from typing import assert_never

from cobalt_wren.config.models import (
    CheckpointStoreSettings,
    FilesystemCheckpointStoreSettings,
    MemoryCheckpointStoreSettings,
    PostgresCheckpointStoreSettings,
)
from cobalt_wren.integrations.checkpoint import CheckpointStore, FilesystemCheckpointStore, MemoryCheckpointStore, PostgresCheckpointStore

__all__ = ["build_checkpoint_store"]


def build_checkpoint_store(settings: CheckpointStoreSettings) -> CheckpointStore:
    """Construct the configured checkpoint store exactly once."""

    if isinstance(settings, MemoryCheckpointStoreSettings):
        return MemoryCheckpointStore()
    if isinstance(settings, FilesystemCheckpointStoreSettings):
        return FilesystemCheckpointStore(settings.root)
    if isinstance(settings, PostgresCheckpointStoreSettings):
        return PostgresCheckpointStore(settings.dsn, table_name=settings.table_name)
    assert_never(settings)
