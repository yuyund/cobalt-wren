"""Canonical artifact store composition for runtime assembly."""

from __future__ import annotations

from typing import assert_never

from langgraph_automation.integrations.artifact import ArtifactStore, FilesystemArtifactStore, MemoryArtifactStore

from langgraph_automation.config.artifact_store import ArtifactStoreSettings, FilesystemArtifactStoreSettings, MemoryArtifactStoreSettings

__all__ = ["build_artifact_store"]


def build_artifact_store(settings: ArtifactStoreSettings) -> ArtifactStore:
    """Construct the configured artifact store exactly once."""

    if isinstance(settings, MemoryArtifactStoreSettings):
        return MemoryArtifactStore()
    if isinstance(settings, FilesystemArtifactStoreSettings):
        return FilesystemArtifactStore(settings.root)
    assert_never(settings)
