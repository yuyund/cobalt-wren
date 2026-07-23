"""Canonical artifact store composition for runtime assembly."""

from __future__ import annotations

from typing import assert_never

from langgraph_automation.integrations.artifact import ArtifactStore, FilesystemArtifactStore, MemoryArtifactStore, S3ArtifactStore

from langgraph_automation.config.artifact_store import ArtifactStoreSettings, FilesystemArtifactStoreSettings, MemoryArtifactStoreSettings, S3ArtifactStoreSettings

__all__ = ["build_artifact_store"]


def build_artifact_store(settings: ArtifactStoreSettings) -> ArtifactStore:
    """Construct the configured artifact store exactly once."""

    if isinstance(settings, MemoryArtifactStoreSettings):
        return MemoryArtifactStore()
    if isinstance(settings, FilesystemArtifactStoreSettings):
        return FilesystemArtifactStore(settings.root)
    if isinstance(settings, S3ArtifactStoreSettings):
        return S3ArtifactStore(bucket=settings.bucket, prefix=settings.prefix, endpoint_url=settings.endpoint_url, region_name=settings.region_name)
    assert_never(settings)
