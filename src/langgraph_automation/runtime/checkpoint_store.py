"""Canonical checkpoint store composition for runtime assembly."""

from __future__ import annotations

from typing import assert_never

from langgraph_automation.config.models import (
    CheckpointStoreSettings,
    FilesystemCheckpointStoreSettings,
    MemoryCheckpointStoreSettings,
    PostgresCheckpointStoreSettings,
)
from langgraph_automation.integrations.checkpoint import CheckpointStore, FilesystemCheckpointStore, MemoryCheckpointStore, PostgresCheckpointStore

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
