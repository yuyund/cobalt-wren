"""In-memory artifact store for control-plane tests and current runtime wiring."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256

from langgraph_automation.api.errors import ArtifactConflictError, ArtifactIntegrityError, ArtifactValidationError

from .base import (
    ArtifactReadResult,
    ArtifactStore,
    ArtifactWriteRequest,
    StoredArtifact,
    normalize_artifact_run_id,
    normalize_artifact_storage_key,
)

_COMPONENT = 'artifact_store'


@dataclass(frozen=True, slots=True)
class _StoredArtifactRecord:
    artifact: StoredArtifact
    body: bytes = b''


class MemoryArtifactStore(ArtifactStore):
    """In-memory artifact store.

    This implementation stores body bytes and normalized descriptors in process
    memory only. It is ephemeral and intentionally non-durable.
    """

    def __init__(self) -> None:
        self._items: dict[str, _StoredArtifactRecord] = {}

    @staticmethod
    def _clone_artifact(artifact: StoredArtifact) -> StoredArtifact:
        return StoredArtifact(
            run_id=artifact.run_id,
            storage_key=artifact.storage_key,
            name=artifact.name,
            kind=artifact.kind,
            content_type=artifact.content_type,
            size=artifact.size,
            digest=artifact.digest,
            metadata=deepcopy(artifact.metadata),
        )

    @staticmethod
    def _digest_body(body: bytes) -> str:
        return f"sha256:{sha256(body).hexdigest()}"

    @classmethod
    def _build_descriptor(cls, request: ArtifactWriteRequest) -> StoredArtifact:
        return StoredArtifact(
            run_id=request.run_id,
            storage_key=request.storage_key,
            name=request.name,
            kind=request.kind,
            content_type=request.content_type,
            size=len(request.body),
            digest=cls._digest_body(request.body),
            metadata=deepcopy(request.metadata),
        )

    @staticmethod
    def _equivalent(existing: _StoredArtifactRecord, request: ArtifactWriteRequest, candidate: StoredArtifact) -> bool:
        return existing.artifact == candidate and existing.body == request.body

    def put(self, request: ArtifactWriteRequest) -> StoredArtifact:
        try:
            validated_storage_key = normalize_artifact_storage_key(request.storage_key)
        except ValueError as exc:
            raise ArtifactValidationError(
                'Artifact store rejected an invalid storage key.',
                code='ARTIFACT_STORE_INVALID_STORAGE_KEY',
                component=_COMPONENT,
            ) from exc
        if validated_storage_key != request.storage_key:
            request = ArtifactWriteRequest(
                run_id=request.run_id,
                storage_key=validated_storage_key,
                body=request.body,
                name=request.name,
                kind=request.kind,
                content_type=request.content_type,
                metadata=deepcopy(request.metadata),
            )

        candidate = self._build_descriptor(request)
        existing = self._items.get(candidate.storage_key)
        if existing is not None:
            if self._equivalent(existing, request, candidate):
                return self._clone_artifact(existing.artifact)
            raise ArtifactConflictError(
                'Artifact store rejected a conflicting write request.',
                code='ARTIFACT_STORE_CONFLICT',
                component=_COMPONENT,
                metadata={'storage_key': candidate.storage_key, 'run_id': candidate.run_id},
            )

        self._items[candidate.storage_key] = _StoredArtifactRecord(artifact=self._clone_artifact(candidate), body=bytes(request.body))
        return self._clone_artifact(candidate)

    def get(self, storage_key: str) -> ArtifactReadResult | None:
        try:
            normalized_storage_key = normalize_artifact_storage_key(storage_key)
        except ValueError as exc:
            raise ArtifactValidationError(
                'Artifact store rejected an invalid storage key.',
                code='ARTIFACT_STORE_INVALID_STORAGE_KEY',
                component=_COMPONENT,
            ) from exc
        record = self._items.get(normalized_storage_key)
        if record is None:
            return None
        artifact = record.artifact
        body = record.body
        expected_digest = self._digest_body(body)
        if artifact.size != len(body) or artifact.digest != expected_digest:
            raise ArtifactIntegrityError(
                'Artifact store detected an integrity failure.',
                code='ARTIFACT_STORE_INTEGRITY_FAILURE',
                component=_COMPONENT,
                metadata={'storage_key': artifact.storage_key},
            )
        return ArtifactReadResult(artifact=self._clone_artifact(artifact), body=bytes(body))

    def list_for_run(self, run_id: int | str) -> list[StoredArtifact]:
        normalized_run_id = normalize_artifact_run_id(run_id)
        result = [
            self._clone_artifact(record.artifact)
            for record in self._items.values()
            if record.artifact.run_id == normalized_run_id
        ]
        result.sort(key=lambda artifact: artifact.storage_key)
        return result
