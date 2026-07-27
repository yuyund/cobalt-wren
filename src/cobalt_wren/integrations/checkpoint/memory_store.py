"""In-memory checkpoint store for the versioned checkpoint protocol."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
from threading import RLock

from cobalt_wren.api.errors import CheckpointConflictError, CheckpointIntegrityError, CheckpointValidationError

from .base import (
    CheckpointReadResult,
    CheckpointStore,
    CheckpointWriteRequest,
    StoredCheckpoint,
    canonicalize_checkpoint_metadata,
    normalize_checkpoint_namespace,
    normalize_checkpoint_run_id,
)

_COMPONENT = 'checkpoint_store'


@dataclass(slots=True)
class _MemoryCheckpointRecord:
    descriptor: StoredCheckpoint
    body: bytes


@dataclass(slots=True)
class _MemoryCheckpointStream:
    records_by_id: dict[str, _MemoryCheckpointRecord]
    records_by_revision: dict[int, str]
    head_checkpoint_id: str | None


class MemoryCheckpointStore(CheckpointStore):
    """Thread-safe EPHEMERAL checkpoint store reference implementation."""

    def __init__(self) -> None:
        self._streams: dict[tuple[int | str, str], _MemoryCheckpointStream] = {}
        self._lock = RLock()

    @staticmethod
    def _body_digest(body: bytes) -> str:
        return f"sha256:{sha256(body).hexdigest()}"

    @staticmethod
    def _clone_checkpoint(checkpoint: StoredCheckpoint) -> StoredCheckpoint:
        return StoredCheckpoint(
            run_id=checkpoint.run_id,
            checkpoint_namespace=checkpoint.checkpoint_namespace,
            checkpoint_id=checkpoint.checkpoint_id,
            parent_checkpoint_id=checkpoint.parent_checkpoint_id,
            revision=checkpoint.revision,
            serializer_name=checkpoint.serializer_name,
            serializer_version=checkpoint.serializer_version,
            content_type=checkpoint.content_type,
            size=checkpoint.size,
            digest=checkpoint.digest,
            metadata=deepcopy(dict(checkpoint.metadata)),
        )

    @classmethod
    def _build_descriptor(cls, request: CheckpointWriteRequest, *, revision: int) -> StoredCheckpoint:
        return StoredCheckpoint(
            run_id=request.run_id,
            checkpoint_namespace=request.checkpoint_namespace,
            checkpoint_id=request.checkpoint_id,
            parent_checkpoint_id=request.parent_checkpoint_id,
            revision=revision,
            serializer_name=request.serializer_name,
            serializer_version=request.serializer_version,
            content_type=request.content_type,
            size=len(request.body),
            digest=cls._body_digest(request.body),
            metadata=deepcopy(dict(request.metadata)),
        )

    @staticmethod
    def _same_canonical_request(existing: _MemoryCheckpointRecord, request: CheckpointWriteRequest) -> bool:
        descriptor = existing.descriptor
        return (
            descriptor.run_id == request.run_id
            and descriptor.checkpoint_namespace == request.checkpoint_namespace
            and descriptor.checkpoint_id == request.checkpoint_id
            and descriptor.parent_checkpoint_id == request.parent_checkpoint_id
            and existing.body == request.body
            and descriptor.serializer_name == request.serializer_name
            and descriptor.serializer_version == request.serializer_version
            and descriptor.content_type == request.content_type
            and canonicalize_checkpoint_metadata(descriptor.metadata) == canonicalize_checkpoint_metadata(request.metadata)
        )

    @staticmethod
    def _verify_record(record: _MemoryCheckpointRecord) -> None:
        descriptor = record.descriptor
        body = record.body
        expected_digest = MemoryCheckpointStore._body_digest(body)
        if descriptor.size != len(body) or descriptor.digest != expected_digest:
            raise CheckpointIntegrityError(
                'Checkpoint store detected an integrity failure.',
                code='CHECKPOINT_STORE_INTEGRITY_FAILURE',
                component=_COMPONENT,
                metadata={'checkpoint_id': descriptor.checkpoint_id},
            )

    @staticmethod
    def _verify_listing_record(record: _MemoryCheckpointRecord) -> None:
        descriptor = record.descriptor
        body = record.body
        if descriptor.size != len(body):
            raise CheckpointIntegrityError(
                'Checkpoint store detected an integrity failure.',
                code='CHECKPOINT_STORE_INTEGRITY_FAILURE',
                component=_COMPONENT,
                metadata={'checkpoint_id': descriptor.checkpoint_id},
            )

    @staticmethod
    def _clone_read_result(record: _MemoryCheckpointRecord) -> CheckpointReadResult:
        return CheckpointReadResult(
            checkpoint=MemoryCheckpointStore._clone_checkpoint(record.descriptor),
            body=bytes(record.body),
        )

    def _stream_key(self, run_id: int | str, checkpoint_namespace: str) -> tuple[int | str, str]:
        return (normalize_checkpoint_run_id(run_id), normalize_checkpoint_namespace(checkpoint_namespace))

    def _get_stream(self, stream_key: tuple[int | str, str]) -> _MemoryCheckpointStream | None:
        return self._streams.get(stream_key)

    def _ensure_stream(self, stream_key: tuple[int | str, str]) -> _MemoryCheckpointStream:
        stream = self._streams.get(stream_key)
        if stream is None:
            stream = _MemoryCheckpointStream(records_by_id={}, records_by_revision={}, head_checkpoint_id=None)
            self._streams[stream_key] = stream
        return stream

    def save(self, request: CheckpointWriteRequest) -> StoredCheckpoint:
        if not isinstance(request, CheckpointWriteRequest):
            raise TypeError('request must be a CheckpointWriteRequest')

        stream_key = self._stream_key(request.run_id, request.checkpoint_namespace)
        with self._lock:
            stream = self._ensure_stream(stream_key)
            existing = stream.records_by_id.get(request.checkpoint_id)
            if existing is not None:
                self._verify_record(existing)
                if self._same_canonical_request(existing, request):
                    return self._clone_checkpoint(existing.descriptor)
                raise CheckpointConflictError(
                    'Checkpoint identity conflicts with an existing immutable version.',
                    code='CHECKPOINT_STORE_CONFLICT',
                    component=_COMPONENT,
                    metadata={'checkpoint_id': request.checkpoint_id},
                )

            head_checkpoint_id = stream.head_checkpoint_id
            if head_checkpoint_id is None:
                if request.parent_checkpoint_id is not None:
                    raise CheckpointConflictError(
                        'Checkpoint write conflicts with the current stream head.',
                        code='CHECKPOINT_STORE_STALE_PARENT',
                        component=_COMPONENT,
                        metadata={'checkpoint_id': request.checkpoint_id},
                    )
                revision = 1
            else:
                head_record = stream.records_by_id.get(head_checkpoint_id)
                if head_record is None:
                    raise CheckpointIntegrityError(
                        'Checkpoint store detected an integrity failure.',
                        code='CHECKPOINT_STORE_INTEGRITY_FAILURE',
                        component=_COMPONENT,
                        metadata={'checkpoint_id': head_checkpoint_id},
                    )
                self._verify_record(head_record)
                if request.parent_checkpoint_id != head_checkpoint_id:
                    raise CheckpointConflictError(
                        'Checkpoint write conflicts with the current stream head.',
                        code='CHECKPOINT_STORE_STALE_PARENT',
                        component=_COMPONENT,
                        metadata={'checkpoint_id': request.checkpoint_id},
                    )
                revision = head_record.descriptor.revision + 1

            descriptor = self._build_descriptor(request, revision=revision)
            record = _MemoryCheckpointRecord(descriptor=descriptor, body=bytes(request.body))
            stream.records_by_id[request.checkpoint_id] = record
            stream.records_by_revision[revision] = request.checkpoint_id
            stream.head_checkpoint_id = request.checkpoint_id
            return self._clone_checkpoint(descriptor)

    def load_latest(self, run_id: int | str, *, checkpoint_namespace: str = '') -> CheckpointReadResult | None:
        stream_key = self._stream_key(run_id, checkpoint_namespace)
        with self._lock:
            stream = self._get_stream(stream_key)
            if stream is None or stream.head_checkpoint_id is None:
                return None
            record = stream.records_by_id.get(stream.head_checkpoint_id)
            if record is None:
                raise CheckpointIntegrityError(
                    'Checkpoint store detected an integrity failure.',
                    code='CHECKPOINT_STORE_INTEGRITY_FAILURE',
                    component=_COMPONENT,
                    metadata={'checkpoint_id': stream.head_checkpoint_id},
                )
            self._verify_record(record)
            return self._clone_read_result(record)

    def load_checkpoint(self, run_id: int | str, checkpoint_id: str, *, checkpoint_namespace: str = '') -> CheckpointReadResult | None:
        stream_key = self._stream_key(run_id, checkpoint_namespace)
        normalized_checkpoint_id = request_checkpoint_id = checkpoint_id
        if not isinstance(request_checkpoint_id, str):
            raise CheckpointValidationError(
                'Checkpoint store rejected an invalid checkpoint identifier.',
                code='CHECKPOINT_STORE_INVALID_CHECKPOINT_ID',
                component=_COMPONENT,
            )
        normalized_checkpoint_id = request_checkpoint_id.strip()
        if normalized_checkpoint_id != request_checkpoint_id or not normalized_checkpoint_id:
            raise CheckpointValidationError(
                'Checkpoint store rejected an invalid checkpoint identifier.',
                code='CHECKPOINT_STORE_INVALID_CHECKPOINT_ID',
                component=_COMPONENT,
            )
        with self._lock:
            stream = self._get_stream(stream_key)
            if stream is None:
                return None
            record = stream.records_by_id.get(normalized_checkpoint_id)
            if record is None:
                return None
            self._verify_record(record)
            return self._clone_read_result(record)

    def list_for_run(self, run_id: int | str, *, checkpoint_namespace: str = '') -> list[StoredCheckpoint]:
        stream_key = self._stream_key(run_id, checkpoint_namespace)
        with self._lock:
            stream = self._get_stream(stream_key)
            if stream is None:
                return []
            results: list[StoredCheckpoint] = []
            for revision in sorted(stream.records_by_revision):
                checkpoint_id = stream.records_by_revision.get(revision)
                if checkpoint_id is None:
                    raise CheckpointIntegrityError(
                        'Checkpoint store detected an integrity failure.',
                        code='CHECKPOINT_STORE_INTEGRITY_FAILURE',
                        component=_COMPONENT,
                        metadata={'revision': revision},
                    )
                record = stream.records_by_id.get(checkpoint_id)
                if record is None:
                    raise CheckpointIntegrityError(
                        'Checkpoint store detected an integrity failure.',
                        code='CHECKPOINT_STORE_INTEGRITY_FAILURE',
                        component=_COMPONENT,
                        metadata={'checkpoint_id': checkpoint_id},
                    )
                self._verify_listing_record(record)
                results.append(self._clone_checkpoint(record.descriptor))
            return results
