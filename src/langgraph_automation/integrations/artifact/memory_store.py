'''In-memory artifact store for control-plane tests and current runtime wiring.'''

from __future__ import annotations

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

    def put(self, artifact: ArtifactWriteResult) -> ArtifactWriteResult:
        validated = replace(artifact, storage_key=validate_storage_key(artifact.storage_key))
        self._items[validated.storage_key] = validated
        return validated

    def get(self, artifact_id: str) -> ArtifactWriteResult | None:
        return self._items.get(artifact_id)

    def list_for_run(self, run_id: int) -> list[ArtifactWriteResult]:
        return [item for item in self._items.values() if item.metadata.get('run_id') == run_id]
