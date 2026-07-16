'''In-memory artifact store for control-plane tests and current runtime wiring.'''

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace

from .base import ArtifactStore, ArtifactWriteResult
from .keys import validate_storage_key


class MemoryArtifactStore(ArtifactStore):
    '''In-memory artifact store.

    This implementation stores normalized artifact metadata in process memory only.
    It does not persist artifact bodies and is not a filesystem-backed store.
    '''

    def __init__(self) -> None:
        self._items: dict[str, ArtifactWriteResult] = {}

    @staticmethod
    def _clone_artifact(artifact: ArtifactWriteResult) -> ArtifactWriteResult:
        return replace(artifact, metadata=deepcopy(artifact.metadata))

    def put(self, artifact: ArtifactWriteResult) -> ArtifactWriteResult:
        validated = replace(artifact, storage_key=validate_storage_key(artifact.storage_key))
        stored = self._clone_artifact(validated)
        self._items[stored.storage_key] = stored
        return self._clone_artifact(stored)

    def get(self, artifact_id: str) -> ArtifactWriteResult | None:
        artifact = self._items.get(artifact_id)
        return None if artifact is None else self._clone_artifact(artifact)

    def list_for_run(self, run_id: int) -> list[ArtifactWriteResult]:
        return [self._clone_artifact(item) for item in self._items.values() if item.metadata.get('run_id') == run_id]
