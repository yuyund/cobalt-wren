"""Process-durable filesystem checkpoint store."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import uuid
from collections.abc import Iterable, Iterator, Mapping
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Any

from langgraph_automation.api.errors import CheckpointConflictError, CheckpointIntegrityError, CheckpointPersistenceError, CheckpointStoreError, CheckpointValidationError

from .base import (
    CheckpointReadResult,
    CheckpointStore,
    CheckpointWriteRequest,
    StoredCheckpoint,
    canonicalize_checkpoint_metadata,
    normalize_checkpoint_id,
    normalize_checkpoint_namespace,
    normalize_checkpoint_run_id,
)

__all__ = ['FilesystemCheckpointStore']

_CHECKPOINT_COMPONENT = 'checkpoint_store'
_SCHEMA_VERSION = 1
_MAX_JSON_BYTES = 1 << 20
_REVISION_WIDTH = 20

try:  # pragma: no cover - imported on POSIX in CI
    import fcntl
except Exception:  # pragma: no cover - unsupported platform
    fcntl = None  # type: ignore[assignment]


@dataclass(frozen=True, slots=True)
class _PublishedBytes:
    created: bool
    path: Path


@dataclass(frozen=True, slots=True)
class _StreamHead:
    run_id: int | str
    checkpoint_namespace: str
    checkpoint_id: str
    revision: int
    record_digest: str


@dataclass(frozen=True, slots=True)
class _PendingIntent:
    run_id: int | str
    checkpoint_namespace: str
    checkpoint_id: str
    parent_checkpoint_id: str | None
    revision: int
    body_digest: str
    record_digest: str


def _validation_error(message: str, *, code: str) -> CheckpointValidationError:
    return CheckpointValidationError(message, code=code, component=_CHECKPOINT_COMPONENT)


def _conflict_error(message: str, *, code: str) -> CheckpointConflictError:
    return CheckpointConflictError(message, code=code, component=_CHECKPOINT_COMPONENT)


def _integrity_error(message: str, *, code: str) -> CheckpointIntegrityError:
    return CheckpointIntegrityError(message, code=code, component=_CHECKPOINT_COMPONENT)


def _persistence_error(message: str, *, code: str, retryable: bool | None = None) -> CheckpointPersistenceError:
    return CheckpointPersistenceError(message, code=code, component=_CHECKPOINT_COMPONENT, retryable=retryable)


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_digest(data: bytes) -> str:
    return f'sha256:{_sha256_hex(data)}'


def _json_bytes(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(',', ':'),
        ensure_ascii=False,
        allow_nan=False,
    ).encode('utf-8')


def _reject_duplicate_keys(pairs: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, value in pairs:
        if key in payload:
            raise ValueError('duplicate JSON key')
        payload[key] = value
    return payload


def _decode_json_object(data: bytes, *, max_bytes: int) -> dict[str, Any]:
    if len(data) > max_bytes:
        raise ValueError('JSON payload too large')

    def _parse_constant(_: str) -> None:
        raise ValueError('invalid JSON constant')

    parsed = json.loads(
        data.decode('utf-8'),
        object_pairs_hook=_reject_duplicate_keys,
        parse_constant=_parse_constant,
    )
    if not isinstance(parsed, dict):
        raise ValueError('JSON payload must be an object')
    return parsed


def _copy_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
    return deepcopy(dict(metadata))


def _safe_record_payload(descriptor: StoredCheckpoint) -> dict[str, Any]:
    payload = {
        'schema_version': _SCHEMA_VERSION,
        'run_id': descriptor.run_id,
        'checkpoint_namespace': descriptor.checkpoint_namespace,
        'checkpoint_id': descriptor.checkpoint_id,
        'parent_checkpoint_id': descriptor.parent_checkpoint_id,
        'revision': descriptor.revision,
        'serializer_name': descriptor.serializer_name,
        'serializer_version': descriptor.serializer_version,
        'content_type': descriptor.content_type,
        'size': descriptor.size,
        'digest': descriptor.digest,
        'metadata': dict(descriptor.metadata),
    }
    canonical = dict(payload)
    canonical['record_digest'] = _sha256_digest(_json_bytes(payload))
    return canonical


def _record_digest(payload: Mapping[str, Any]) -> str:
    payload_without_digest = dict(payload)
    payload_without_digest.pop('record_digest', None)
    return _sha256_digest(_json_bytes(payload_without_digest))


def _stream_identity_bytes(run_id: int | str, checkpoint_namespace: str) -> bytes:
    if isinstance(run_id, int):
        run_id_payload: dict[str, Any] = {'type': 'int', 'value': run_id}
    else:
        run_id_payload = {'type': 'str', 'value': run_id}
    payload = {
        'schema_version': _SCHEMA_VERSION,
        'run_id': run_id_payload,
        'checkpoint_namespace': checkpoint_namespace,
    }
    return _json_bytes(payload)


def _checkpoint_id_bytes(checkpoint_id: str) -> bytes:
    return checkpoint_id.encode('utf-8')


def _revision_filename(revision: int) -> str:
    if revision <= 0:
        raise _integrity_error(
            'Checkpoint store detected an invalid checkpoint revision.',
            code='CHECKPOINT_STORE_INVALID_REVISION',
        )
    return f'{revision:0{_REVISION_WIDTH}d}.json'


class FilesystemCheckpointStore(CheckpointStore):
    """Process-durable checkpoint store backed by immutable filesystem records."""

    def __init__(self, root: str | os.PathLike[str]) -> None:
        root_path = Path(root)
        if not root_path.is_absolute():
            raise _validation_error(
                'Filesystem checkpoint store requires an absolute root path.',
                code='CHECKPOINT_STORE_INVALID_ROOT',
            )
        self._root = root_path
        self._stream_lock_guard = RLock()
        self._stream_locks: dict[tuple[int | str, str], RLock] = {}
        self._ensure_directory_chain(self._root)
        self._ensure_directory_chain(self._root / 'bodies' / 'sha256')
        self._ensure_directory_chain(self._root / 'streams' / 'sha256')

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(root=<trusted>)'

    @property
    def _is_supported_platform(self) -> bool:
        return fcntl is not None

    def _check_supported_platform(self) -> None:
        if not self._is_supported_platform:
            raise _persistence_error(
                'Filesystem checkpoint store requires POSIX advisory locking support.',
                code='CHECKPOINT_STORE_PLATFORM_UNSUPPORTED',
            )

    def _stream_key(self, run_id: int | str, checkpoint_namespace: str) -> tuple[int | str, str]:
        return (
            normalize_checkpoint_run_id(run_id),
            normalize_checkpoint_namespace(checkpoint_namespace),
        )

    def _get_stream_lock(self, stream_key: tuple[int | str, str]) -> RLock:
        with self._stream_lock_guard:
            lock = self._stream_locks.get(stream_key)
            if lock is None:
                lock = RLock()
                self._stream_locks[stream_key] = lock
            return lock

    def _stream_digest(self, stream_key: tuple[int | str, str]) -> str:
        return _sha256_hex(_stream_identity_bytes(stream_key[0], stream_key[1]))

    def _checkpoint_id_digest(self, checkpoint_id: str) -> str:
        return _sha256_hex(_checkpoint_id_bytes(checkpoint_id))

    def _stream_dir(self, stream_key: tuple[int | str, str]) -> Path:
        digest = self._stream_digest(stream_key)
        return self._root / 'streams' / 'sha256' / digest[:2] / digest[2:4] / digest

    def _body_path(self, digest: str) -> Path:
        suffix = digest.removeprefix('sha256:')
        return self._root / 'bodies' / 'sha256' / suffix[:2] / suffix[2:4] / f'{suffix}.blob'

    def _by_id_path(self, stream_key: tuple[int | str, str], checkpoint_id: str) -> Path:
        digest = self._checkpoint_id_digest(checkpoint_id)
        stream_dir = self._stream_dir(stream_key)
        return stream_dir / 'records' / 'by-id' / digest[:2] / digest[2:4] / f'{digest}.json'

    def _by_revision_path(self, stream_key: tuple[int | str, str], revision: int) -> Path:
        stream_dir = self._stream_dir(stream_key)
        return stream_dir / 'records' / 'by-revision' / _revision_filename(revision)

    def _lock_path(self, stream_key: tuple[int | str, str]) -> Path:
        return self._stream_dir(stream_key) / 'lock'

    def _head_path(self, stream_key: tuple[int | str, str]) -> Path:
        return self._stream_dir(stream_key) / 'head.json'

    def _pending_path(self, stream_key: tuple[int | str, str]) -> Path:
        return self._stream_dir(stream_key) / 'pending.json'

    def _ensure_directory_chain(self, path: Path) -> None:
        current = Path(path.anchor) if path.is_absolute() else Path()
        for part in path.parts[1:] if path.is_absolute() else path.parts:
            current = current / part
            self._ensure_directory(current)

    def _ensure_directory(self, path: Path) -> None:
        try:
            if path.is_symlink():
                raise _persistence_error(
                    'Filesystem checkpoint store root is unavailable.',
                    code='CHECKPOINT_STORE_DIRECTORY_UNAVAILABLE',
                )
            if path.exists():
                st = path.lstat()
                if not stat.S_ISDIR(st.st_mode):
                    raise _persistence_error(
                        'Filesystem checkpoint store root is unavailable.',
                        code='CHECKPOINT_STORE_DIRECTORY_UNAVAILABLE',
                    )
                return
            try:
                path.mkdir()
            except FileExistsError:
                pass
            st = path.lstat()
            if stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode):
                raise _persistence_error(
                    'Filesystem checkpoint store root is unavailable.',
                    code='CHECKPOINT_STORE_DIRECTORY_UNAVAILABLE',
                )
        except CheckpointStoreError:
            raise
        except OSError as exc:
            raise _persistence_error(
                'Filesystem checkpoint store root is unavailable.',
                code='CHECKPOINT_STORE_DIRECTORY_UNAVAILABLE',
            ) from exc

    def _ensure_parent_directory(self, path: Path) -> None:
        self._ensure_directory_chain(path.parent)

    def _open_no_follow(self, path: Path, flags: int) -> int:
        self._check_supported_platform()
        if hasattr(os, 'O_NOFOLLOW'):
            flags |= os.O_NOFOLLOW
        if hasattr(os, 'O_CLOEXEC'):
            flags |= os.O_CLOEXEC
        try:
            return os.open(path, flags)
        except FileNotFoundError as exc:
            raise exc
        except OSError as exc:
            raise _persistence_error(
                'Filesystem checkpoint store file access failed.',
                code='CHECKPOINT_STORE_FILE_ACCESS_FAILED',
            ) from exc

    def _read_regular_file_bytes(self, path: Path, *, purpose: str, max_bytes: int | None = None, missing_ok: bool = False) -> bytes | None:
        if path.is_symlink():
            raise _integrity_error(
                f'Filesystem checkpoint store detected a {purpose} symlink.',
                code=f'CHECKPOINT_STORE_SYMLINK_{purpose.upper()}',
            )
        if not path.exists():
            if missing_ok:
                return None
            raise _integrity_error(
                f'Filesystem checkpoint store detected a missing {purpose}.',
                code=f'CHECKPOINT_STORE_MISSING_{purpose.upper()}',
            )

        flags = os.O_RDONLY
        try:
            fd = self._open_no_follow(path, flags)
        except FileNotFoundError:
            if missing_ok:
                return None
            raise _integrity_error(
                f'Filesystem checkpoint store detected a missing {purpose}.',
                code=f'CHECKPOINT_STORE_MISSING_{purpose.upper()}',
            ) from None

        try:
            st = os.fstat(fd)
            if not stat.S_ISREG(st.st_mode):
                raise _integrity_error(
                    f'Filesystem checkpoint store detected a non-regular {purpose}.',
                    code=f'CHECKPOINT_STORE_NONREGULAR_{purpose.upper()}',
                )
            if max_bytes is not None and st.st_size > max_bytes:
                raise _integrity_error(
                    f'Filesystem checkpoint store detected an oversized {purpose}.',
                    code=f'CHECKPOINT_STORE_OVERSIZED_{purpose.upper()}',
                )
            chunks: list[bytes] = []
            remaining = st.st_size
            while True:
                chunk = os.read(fd, 65536 if remaining == 0 else min(65536, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                if max_bytes is not None:
                    remaining -= len(chunk)
                    if remaining < 0:
                        raise _integrity_error(
                            f'Filesystem checkpoint store detected an oversized {purpose}.',
                            code=f'CHECKPOINT_STORE_OVERSIZED_{purpose.upper()}',
                        )
            data = b''.join(chunks)
            if len(data) != st.st_size:
                raise _integrity_error(
                    f'Filesystem checkpoint store detected a truncated {purpose}.',
                    code=f'CHECKPOINT_STORE_TRUNCATED_{purpose.upper()}',
                )
            return data
        except CheckpointStoreError:
            raise
        except OSError as exc:
            raise _persistence_error(
                f'Filesystem checkpoint store failed while reading a {purpose}.',
                code=f'CHECKPOINT_STORE_READ_FAILED_{purpose.upper()}',
            ) from exc
        finally:
            try:
                os.close(fd)
            except OSError:
                pass

    def _write_temp_bytes(self, directory: Path, payload: bytes, *, suffix: str = '.tmp') -> Path:
        self._ensure_directory_chain(directory)
        temp_name = f'.tmp-{uuid.uuid4().hex}{suffix}'
        temp_path = directory / temp_name
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
        if hasattr(os, 'O_CLOEXEC'):
            flags |= os.O_CLOEXEC
        fd: int | None = None
        try:
            fd = os.open(temp_path, flags, 0o600)
            view = memoryview(payload)
            total = 0
            while total < len(view):
                written = os.write(fd, view[total:])
                if written == 0:
                    raise _persistence_error(
                        'Filesystem checkpoint store failed while writing a file.',
                        code='CHECKPOINT_STORE_WRITE_FAILED',
                    )
                total += written
            os.fsync(fd)
            return temp_path
        except CheckpointStoreError:
            raise
        except OSError as exc:
            raise _persistence_error(
                'Filesystem checkpoint store failed while writing a file.',
                code='CHECKPOINT_STORE_WRITE_FAILED',
            ) from exc
        finally:
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass

    def _link_no_overwrite(self, source: Path, final_path: Path) -> bool:
        self._ensure_parent_directory(final_path)
        try:
            os.link(source, final_path)
            return True
        except FileExistsError:
            return False
        except OSError as exc:
            raise _persistence_error(
                'Filesystem checkpoint store publication failed.',
                code='CHECKPOINT_STORE_PUBLICATION_UNSUPPORTED',
            ) from exc

    def _cleanup_path(self, path: Path) -> None:
        try:
            if path.exists():
                path.unlink()
        except OSError:
            pass

    def _publish_immutable_bytes(self, final_path: Path, payload: bytes) -> _PublishedBytes:
        temp_path = self._write_temp_bytes(final_path.parent, payload)
        try:
            created = self._link_no_overwrite(temp_path, final_path)
            if created:
                self._fsync_directory(final_path.parent)
            return _PublishedBytes(created=created, path=final_path)
        finally:
            self._cleanup_path(temp_path)

    def _publish_immutable_link(self, source: Path, final_path: Path) -> bool:
        return self._link_no_overwrite(source, final_path)

    def _read_canonical_json(self, path: Path, *, purpose: str, max_bytes: int | None = None, missing_ok: bool = False) -> dict[str, Any] | None:
        data = self._read_regular_file_bytes(path, purpose=purpose, max_bytes=max_bytes, missing_ok=missing_ok)
        if data is None:
            return None
        try:
            payload = _decode_json_object(data, max_bytes=max_bytes or _MAX_JSON_BYTES)
        except (UnicodeDecodeError, ValueError) as exc:
            raise _integrity_error(
                f'Filesystem checkpoint store detected an invalid {purpose}.',
                code=f'CHECKPOINT_STORE_INVALID_{purpose.upper()}',
            ) from exc
        canonical_bytes = _json_bytes(payload)
        if canonical_bytes != data:
            raise _integrity_error(
                f'Filesystem checkpoint store detected a noncanonical {purpose}.',
                code=f'CHECKPOINT_STORE_NONCANONICAL_{purpose.upper()}',
            )
        return payload

    def _normalize_record_payload(self, payload: Mapping[str, Any], *, path: Path) -> StoredCheckpoint:
        required_keys = {
            'schema_version',
            'run_id',
            'checkpoint_namespace',
            'checkpoint_id',
            'parent_checkpoint_id',
            'revision',
            'serializer_name',
            'serializer_version',
            'content_type',
            'size',
            'digest',
            'metadata',
            'record_digest',
        }
        if set(payload) != required_keys:
            raise _integrity_error(
                'Filesystem checkpoint store detected an invalid record.',
                code='CHECKPOINT_STORE_INVALID_RECORD',
            )
        if payload['schema_version'] != _SCHEMA_VERSION:
            raise _integrity_error(
                'Filesystem checkpoint store detected an unsupported record schema.',
                code='CHECKPOINT_STORE_UNSUPPORTED_SCHEMA',
            )
        record_digest = payload['record_digest']
        if not isinstance(record_digest, str) or not record_digest.startswith('sha256:') or len(record_digest) != len('sha256:') + 64:
            raise _integrity_error(
                'Filesystem checkpoint store detected an invalid record digest.',
                code='CHECKPOINT_STORE_INVALID_RECORD_DIGEST',
            )
        canonical_digest = _record_digest(payload)
        if canonical_digest != record_digest:
            raise _integrity_error(
                'Filesystem checkpoint store detected a record digest mismatch.',
                code='CHECKPOINT_STORE_RECORD_DIGEST_MISMATCH',
            )
        try:
            descriptor = StoredCheckpoint(
                run_id=normalize_checkpoint_run_id(payload['run_id']),
                checkpoint_namespace=normalize_checkpoint_namespace(payload['checkpoint_namespace']),
                checkpoint_id=normalize_checkpoint_id(payload['checkpoint_id']),
                parent_checkpoint_id=None if payload['parent_checkpoint_id'] is None else normalize_checkpoint_id(payload['parent_checkpoint_id']),
                revision=payload['revision'],
                serializer_name=payload['serializer_name'],
                serializer_version=payload['serializer_version'],
                content_type=payload['content_type'],
                size=payload['size'],
                digest=payload['digest'],
                metadata=payload['metadata'],
            )
        except CheckpointStoreError as exc:
            raise _integrity_error(
                'Filesystem checkpoint store detected an invalid record.',
                code='CHECKPOINT_STORE_INVALID_RECORD',
            ) from exc
        return descriptor

    def _record_from_path(self, path: Path) -> StoredCheckpoint:
        payload = self._read_canonical_json(path, purpose='record', max_bytes=_MAX_JSON_BYTES)
        if payload is None:
            raise _integrity_error(
                'Filesystem checkpoint store detected a missing record.',
                code='CHECKPOINT_STORE_MISSING_RECORD',
            )
        return self._normalize_record_payload(payload, path=path)

    def _head_from_path(self, path: Path) -> _StreamHead:
        payload = self._read_canonical_json(path, purpose='head', max_bytes=_MAX_JSON_BYTES)
        if payload is None:
            raise _integrity_error(
                'Filesystem checkpoint store detected a missing head.',
                code='CHECKPOINT_STORE_MISSING_HEAD',
            )
        required_keys = {'schema_version', 'run_id', 'checkpoint_namespace', 'checkpoint_id', 'revision', 'record_digest'}
        if set(payload) != required_keys:
            raise _integrity_error(
                'Filesystem checkpoint store detected an invalid head.',
                code='CHECKPOINT_STORE_INVALID_HEAD',
            )
        if payload['schema_version'] != _SCHEMA_VERSION:
            raise _integrity_error(
                'Filesystem checkpoint store detected an unsupported head schema.',
                code='CHECKPOINT_STORE_UNSUPPORTED_HEAD_SCHEMA',
            )
        try:
            return _StreamHead(
                run_id=normalize_checkpoint_run_id(payload['run_id']),
                checkpoint_namespace=normalize_checkpoint_namespace(payload['checkpoint_namespace']),
                checkpoint_id=normalize_checkpoint_id(payload['checkpoint_id']),
                revision=payload['revision'],
                record_digest=payload['record_digest'],
            )
        except CheckpointStoreError as exc:
            raise _integrity_error(
                'Filesystem checkpoint store detected an invalid head.',
                code='CHECKPOINT_STORE_INVALID_HEAD',
            ) from exc

    def _pending_from_path(self, path: Path) -> _PendingIntent:
        payload = self._read_canonical_json(path, purpose='pending', max_bytes=_MAX_JSON_BYTES)
        if payload is None:
            raise _integrity_error(
                'Filesystem checkpoint store detected a missing pending record.',
                code='CHECKPOINT_STORE_MISSING_PENDING',
            )
        required_keys = {'schema_version', 'run_id', 'checkpoint_namespace', 'checkpoint_id', 'parent_checkpoint_id', 'revision', 'body_digest', 'record_digest'}
        if set(payload) != required_keys:
            raise _integrity_error(
                'Filesystem checkpoint store detected an invalid pending record.',
                code='CHECKPOINT_STORE_INVALID_PENDING',
            )
        if payload['schema_version'] != _SCHEMA_VERSION:
            raise _integrity_error(
                'Filesystem checkpoint store detected an unsupported pending schema.',
                code='CHECKPOINT_STORE_UNSUPPORTED_PENDING_SCHEMA',
            )
        try:
            return _PendingIntent(
                run_id=normalize_checkpoint_run_id(payload['run_id']),
                checkpoint_namespace=normalize_checkpoint_namespace(payload['checkpoint_namespace']),
                checkpoint_id=normalize_checkpoint_id(payload['checkpoint_id']),
                parent_checkpoint_id=None if payload['parent_checkpoint_id'] is None else normalize_checkpoint_id(payload['parent_checkpoint_id']),
                revision=payload['revision'],
                body_digest=payload['body_digest'],
                record_digest=payload['record_digest'],
            )
        except CheckpointStoreError as exc:
            raise _integrity_error(
                'Filesystem checkpoint store detected an invalid pending record.',
                code='CHECKPOINT_STORE_INVALID_PENDING',
            ) from exc

    def _checkpoint_descriptor(self, request: CheckpointWriteRequest, *, revision: int) -> StoredCheckpoint:
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
            digest=_sha256_digest(request.body),
            metadata=_copy_metadata(request.metadata),
        )

    def _same_canonical_request(self, descriptor: StoredCheckpoint, request: CheckpointWriteRequest) -> bool:
        return (
            descriptor.run_id == request.run_id
            and descriptor.checkpoint_namespace == request.checkpoint_namespace
            and descriptor.checkpoint_id == request.checkpoint_id
            and descriptor.parent_checkpoint_id == request.parent_checkpoint_id
            and descriptor.serializer_name == request.serializer_name
            and descriptor.serializer_version == request.serializer_version
            and descriptor.content_type == request.content_type
            and descriptor.size == len(request.body)
            and descriptor.digest == _sha256_digest(request.body)
            and canonicalize_checkpoint_metadata(descriptor.metadata) == canonicalize_checkpoint_metadata(request.metadata)
        )

    def _write_head(self, stream_key: tuple[int | str, str], head: _StreamHead) -> None:
        head_path = self._head_path(stream_key)
        payload = {
            'schema_version': _SCHEMA_VERSION,
            'run_id': head.run_id,
            'checkpoint_namespace': head.checkpoint_namespace,
            'checkpoint_id': head.checkpoint_id,
            'revision': head.revision,
            'record_digest': head.record_digest,
        }
        temp_path = self._write_temp_bytes(head_path.parent, _json_bytes(payload), suffix='.json')
        try:
            os.replace(temp_path, head_path)
            self._fsync_directory(head_path.parent)
        except OSError as exc:
            raise _persistence_error(
                'Filesystem checkpoint store failed to update the stream head.',
                code='CHECKPOINT_STORE_HEAD_UPDATE_FAILED',
            ) from exc
        finally:
            self._cleanup_path(temp_path)

    def _write_pending(self, stream_key: tuple[int | str, str], pending: _PendingIntent) -> None:
        pending_path = self._pending_path(stream_key)
        payload = {
            'schema_version': _SCHEMA_VERSION,
            'run_id': pending.run_id,
            'checkpoint_namespace': pending.checkpoint_namespace,
            'checkpoint_id': pending.checkpoint_id,
            'parent_checkpoint_id': pending.parent_checkpoint_id,
            'revision': pending.revision,
            'body_digest': pending.body_digest,
            'record_digest': pending.record_digest,
        }
        temp_path = self._write_temp_bytes(pending_path.parent, _json_bytes(payload), suffix='.json')
        try:
            if not self._publish_immutable_link(temp_path, pending_path):
                raise _conflict_error(
                    'Filesystem checkpoint store detected a conflicting pending transaction.',
                    code='CHECKPOINT_STORE_PENDING_CONFLICT',
                )
            self._fsync_directory(pending_path.parent)
        except CheckpointStoreError:
            raise
        except OSError as exc:
            raise _persistence_error(
                'Filesystem checkpoint store failed to publish a pending transaction.',
                code='CHECKPOINT_STORE_PENDING_PUBLICATION_FAILED',
            ) from exc
        finally:
            self._cleanup_path(temp_path)

    def _fsync_directory(self, path: Path) -> None:
        if not self._is_supported_platform:
            raise _persistence_error(
                'Filesystem checkpoint store requires POSIX advisory locking support.',
                code='CHECKPOINT_STORE_PLATFORM_UNSUPPORTED',
            )
        flags = os.O_RDONLY
        if hasattr(os, 'O_DIRECTORY'):
            flags |= os.O_DIRECTORY
        if hasattr(os, 'O_CLOEXEC'):
            flags |= os.O_CLOEXEC
        try:
            fd = os.open(path, flags)
        except OSError as exc:
            raise _persistence_error(
                'Filesystem checkpoint store failed to sync a directory.',
                code='CHECKPOINT_STORE_DIRECTORY_SYNC_FAILED',
            ) from exc
        try:
            os.fsync(fd)
        except OSError as exc:
            raise _persistence_error(
                'Filesystem checkpoint store failed to sync a directory.',
                code='CHECKPOINT_STORE_DIRECTORY_SYNC_FAILED',
            ) from exc
        finally:
            try:
                os.close(fd)
            except OSError:
                pass

    @contextmanager
    def _locked_stream(self, stream_key: tuple[int | str, str]) -> Iterator[None]:
        self._check_supported_platform()
        lock = self._get_stream_lock(stream_key)
        lock_path = self._lock_path(stream_key)
        self._ensure_parent_directory(lock_path)
        flags = os.O_RDWR | os.O_CREAT
        if hasattr(os, 'O_CLOEXEC'):
            flags |= os.O_CLOEXEC
        if hasattr(os, 'O_NOFOLLOW'):
            flags |= os.O_NOFOLLOW
        try:
            fd = os.open(lock_path, flags, 0o600)
        except OSError as exc:
            raise _persistence_error(
                'Filesystem checkpoint store failed to acquire a stream lock.',
                code='CHECKPOINT_STORE_LOCK_FAILED',
            ) from exc
        try:
            with lock:
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX)
                except OSError as exc:  # pragma: no cover - exercised in filesystem tests
                    raise _persistence_error(
                        'Filesystem checkpoint store failed to acquire a stream lock.',
                        code='CHECKPOINT_STORE_LOCK_FAILED',
                    ) from exc
                try:
                    yield
                finally:
                    try:
                        fcntl.flock(fd, fcntl.LOCK_UN)
                    except OSError:
                        pass
        finally:
            try:
                os.close(fd)
            except OSError:
                pass

    def _load_head(self, stream_key: tuple[int | str, str]) -> _StreamHead | None:
        head_path = self._head_path(stream_key)
        if self._read_canonical_json(head_path, purpose='head', max_bytes=_MAX_JSON_BYTES, missing_ok=True) is None:
            return None
        return self._head_from_path(head_path)

    def _load_pending(self, stream_key: tuple[int | str, str]) -> _PendingIntent | None:
        pending_path = self._pending_path(stream_key)
        if self._read_canonical_json(pending_path, purpose='pending', max_bytes=_MAX_JSON_BYTES, missing_ok=True) is None:
            return None
        return self._pending_from_path(pending_path)

    def _head_and_records_exist(self, stream_key: tuple[int | str, str]) -> bool:
        stream_dir = self._stream_dir(stream_key)
        if not stream_dir.exists():
            return False
        by_id_root = stream_dir / 'records' / 'by-id'
        by_revision_root = stream_dir / 'records' / 'by-revision'
        for root in (by_id_root, by_revision_root):
            if not root.exists():
                continue
            for path in root.rglob('*.json'):
                if path.is_file():
                    return True
        return False

    def _load_record_by_id(self, stream_key: tuple[int | str, str], checkpoint_id: str, *, verify_body: bool) -> StoredCheckpoint | None:
        path = self._by_id_path(stream_key, checkpoint_id)
        payload = self._read_canonical_json(path, purpose='record', max_bytes=_MAX_JSON_BYTES, missing_ok=True)
        if payload is None:
            return None
        descriptor = self._normalize_record_payload(payload, path=path)
        if verify_body:
            self._verify_record_body(stream_key, descriptor)
        return descriptor

    def _load_record_by_revision(self, stream_key: tuple[int | str, str], revision: int, *, verify_body: bool) -> StoredCheckpoint | None:
        path = self._by_revision_path(stream_key, revision)
        payload = self._read_canonical_json(path, purpose='record', max_bytes=_MAX_JSON_BYTES, missing_ok=True)
        if payload is None:
            return None
        descriptor = self._normalize_record_payload(payload, path=path)
        if verify_body:
            self._verify_record_body(stream_key, descriptor)
        return descriptor

    @staticmethod
    def _verify_hard_link_pair(first: Path, second: Path, *, purpose: str) -> None:
        try:
            first_stat = first.lstat()
            second_stat = second.lstat()
        except FileNotFoundError as exc:
            raise _integrity_error(
                f'Filesystem checkpoint store detected a missing {purpose}.',
                code=f'CHECKPOINT_STORE_MISSING_{purpose.upper()}',
            ) from exc
        if stat.S_ISLNK(first_stat.st_mode) or stat.S_ISLNK(second_stat.st_mode):
            raise _integrity_error(
                f'Filesystem checkpoint store detected a {purpose} symlink.',
                code=f'CHECKPOINT_STORE_SYMLINK_{purpose.upper()}',
            )
        if not stat.S_ISREG(first_stat.st_mode) or not stat.S_ISREG(second_stat.st_mode):
            raise _integrity_error(
                f'Filesystem checkpoint store detected a non-regular {purpose}.',
                code=f'CHECKPOINT_STORE_NONREGULAR_{purpose.upper()}',
            )
        if first_stat.st_dev != second_stat.st_dev or first_stat.st_ino != second_stat.st_ino:
            raise _integrity_error(
                f'Filesystem checkpoint store detected a {purpose} link mismatch.',
                code=f'CHECKPOINT_STORE_LINK_MISMATCH_{purpose.upper()}',
            )

    def _verify_record_body(self, _stream_key: tuple[int | str, str], descriptor: StoredCheckpoint) -> None:
        body_path = self._body_path(descriptor.digest)
        body = self._read_regular_file_bytes(body_path, purpose='body', max_bytes=descriptor.size, missing_ok=False)
        if body is None:
            raise _integrity_error(
                'Filesystem checkpoint store detected a missing body.',
                code='CHECKPOINT_STORE_MISSING_BODY',
            )
        if len(body) != descriptor.size:
            raise _integrity_error(
                'Filesystem checkpoint store detected a body size mismatch.',
                code='CHECKPOINT_STORE_BODY_SIZE_MISMATCH',
            )
        if _sha256_digest(body) != descriptor.digest:
            raise _integrity_error(
                'Filesystem checkpoint store detected a body digest mismatch.',
                code='CHECKPOINT_STORE_BODY_DIGEST_MISMATCH',
            )

    def _validate_committed_chain(self, stream_key: tuple[int | str, str], head: _StreamHead, *, verify_body: bool = True) -> list[StoredCheckpoint]:
        committed: list[StoredCheckpoint] = []
        expected_parent: str | None = None
        for revision in range(1, head.revision + 1):
            record = self._load_record_by_revision(stream_key, revision, verify_body=False)
            if record is None:
                raise _integrity_error(
                    'Filesystem checkpoint store detected a revision gap.',
                    code='CHECKPOINT_STORE_REVISION_GAP',
                )
            if record.revision != revision:
                raise _integrity_error(
                    'Filesystem checkpoint store detected a revision mismatch.',
                    code='CHECKPOINT_STORE_REVISION_MISMATCH',
                )
            if record.parent_checkpoint_id != expected_parent:
                raise _integrity_error(
                    'Filesystem checkpoint store detected a parent chain mismatch.',
                    code='CHECKPOINT_STORE_PARENT_MISMATCH',
                )
            by_id = self._load_record_by_id(stream_key, record.checkpoint_id, verify_body=False)
            if by_id is None or by_id != record:
                raise _integrity_error(
                    'Filesystem checkpoint store detected a record index mismatch.',
                    code='CHECKPOINT_STORE_RECORD_INDEX_MISMATCH',
                )
            self._verify_hard_link_pair(self._by_id_path(stream_key, record.checkpoint_id), self._by_revision_path(stream_key, revision), purpose='record')
            if verify_body:
                self._verify_record_body(stream_key, record)
            else:
                self._validate_listing_body(record)
            committed.append(record)
            expected_parent = record.checkpoint_id
        if not committed or committed[-1].checkpoint_id != head.checkpoint_id or committed[-1].revision != head.revision:
            raise _integrity_error(
                'Filesystem checkpoint store detected a head mismatch.',
                code='CHECKPOINT_STORE_HEAD_MISMATCH',
            )
        if _record_digest(_safe_record_payload(committed[-1])) != head.record_digest:
            raise _integrity_error(
                'Filesystem checkpoint store detected a head digest mismatch.',
                code='CHECKPOINT_STORE_HEAD_DIGEST_MISMATCH',
            )
        return committed

    def _audit_no_extra_finalized_records(
        self,
        stream_key: tuple[int | str, str],
        committed: list[StoredCheckpoint],
    ) -> None:
        committed_by_id = {record.checkpoint_id: record for record in committed}
        committed_by_revision = {record.revision: record for record in committed}
        stream_dir = self._stream_dir(stream_key)
        by_id_root = stream_dir / 'records' / 'by-id'
        by_revision_root = stream_dir / 'records' / 'by-revision'

        for path in by_id_root.rglob('*.json') if by_id_root.exists() else ():
            record = self._record_from_path(path)
            expected = self._by_id_path(stream_key, record.checkpoint_id)
            if path != expected:
                raise _integrity_error(
                    'Filesystem checkpoint store detected a record path mismatch.',
                    code='CHECKPOINT_STORE_RECORD_PATH_MISMATCH',
                )
            committed_record = committed_by_id.get(record.checkpoint_id)
            if committed_record is None or committed_record != record:
                raise _integrity_error(
                    'Filesystem checkpoint store detected an unexpected finalized record.',
                    code='CHECKPOINT_STORE_FINALIZED_RECORD_MISMATCH',
                )
            self._verify_hard_link_pair(expected, self._by_revision_path(stream_key, record.revision), purpose='record')

        for path in by_revision_root.rglob('*.json') if by_revision_root.exists() else ():
            record = self._record_from_path(path)
            expected = self._by_revision_path(stream_key, record.revision)
            if path != expected:
                raise _integrity_error(
                    'Filesystem checkpoint store detected a record path mismatch.',
                    code='CHECKPOINT_STORE_RECORD_PATH_MISMATCH',
                )
            committed_record = committed_by_revision.get(record.revision)
            if committed_record is None or committed_record != record:
                raise _integrity_error(
                    'Filesystem checkpoint store detected an unexpected finalized record.',
                    code='CHECKPOINT_STORE_FINALIZED_RECORD_MISMATCH',
                )

    def _recover_stream(self, stream_key: tuple[int | str, str], *, verify_body: bool) -> None:
        pending = self._load_pending(stream_key)
        head = self._load_head(stream_key)
        if pending is None:
            if head is None:
                if self._head_and_records_exist(stream_key):
                    raise _integrity_error(
                        'Filesystem checkpoint store detected committed records without a head.',
                        code='CHECKPOINT_STORE_DANGLING_RECORDS',
                    )
                return
            self._validate_committed_chain(stream_key, head, verify_body=verify_body)
            return

        by_id = self._load_record_by_id(stream_key, pending.checkpoint_id, verify_body=verify_body)
        by_revision = self._load_record_by_revision(stream_key, pending.revision, verify_body=verify_body)

        if head is not None and head.revision > pending.revision:
            raise _integrity_error(
                'Filesystem checkpoint store detected an impossible pending transaction.',
                code='CHECKPOINT_STORE_IMPOSSIBLE_PENDING',
            )

        if by_id is None and by_revision is None:
            self._cleanup_path(self._pending_path(stream_key))
            if head is not None:
                self._validate_committed_chain(stream_key, head, verify_body=verify_body)
            return

        if by_id is None and by_revision is not None:
            if by_revision.checkpoint_id != pending.checkpoint_id or by_revision.revision != pending.revision or by_revision.parent_checkpoint_id != pending.parent_checkpoint_id:
                raise _integrity_error(
                    'Filesystem checkpoint store detected a pending/record mismatch.',
                    code='CHECKPOINT_STORE_PENDING_RECORD_MISMATCH',
                )
            by_id_path = self._by_id_path(stream_key, pending.checkpoint_id)
            if not self._publish_immutable_link(by_revision_path := self._by_revision_path(stream_key, pending.revision), by_id_path):
                existing = self._load_record_by_id(stream_key, pending.checkpoint_id, verify_body=verify_body)
                if existing is None or existing != by_revision:
                    raise _integrity_error(
                        'Filesystem checkpoint store detected a pending/record mismatch.',
                        code='CHECKPOINT_STORE_PENDING_RECORD_MISMATCH',
                    )
            self._fsync_directory(by_id_path.parent)
            head = _StreamHead(
                run_id=by_revision.run_id,
                checkpoint_namespace=by_revision.checkpoint_namespace,
                checkpoint_id=by_revision.checkpoint_id,
                revision=by_revision.revision,
                record_digest=_record_digest(_safe_record_payload(by_revision)),
            )
            self._write_head(stream_key, head)
            self._cleanup_path(self._pending_path(stream_key))
            return

        if by_id is not None and by_revision is None:
            if by_id.checkpoint_id != pending.checkpoint_id or by_id.revision != pending.revision or by_id.parent_checkpoint_id != pending.parent_checkpoint_id:
                raise _integrity_error(
                    'Filesystem checkpoint store detected a pending/record mismatch.',
                    code='CHECKPOINT_STORE_PENDING_RECORD_MISMATCH',
                )
            by_revision_path = self._by_revision_path(stream_key, pending.revision)
            if not self._publish_immutable_link(self._by_id_path(stream_key, pending.checkpoint_id), by_revision_path):
                existing = self._load_record_by_revision(stream_key, pending.revision, verify_body=verify_body)
                if existing is None or existing != by_id:
                    raise _integrity_error(
                        'Filesystem checkpoint store detected a pending/record mismatch.',
                        code='CHECKPOINT_STORE_PENDING_RECORD_MISMATCH',
                    )
            self._fsync_directory(by_revision_path.parent)
            head = _StreamHead(
                run_id=by_id.run_id,
                checkpoint_namespace=by_id.checkpoint_namespace,
                checkpoint_id=by_id.checkpoint_id,
                revision=by_id.revision,
                record_digest=_record_digest(_safe_record_payload(by_id)),
            )
            self._write_head(stream_key, head)
            self._cleanup_path(self._pending_path(stream_key))
            return

        if by_id is not None and by_revision is not None:
            if by_id != by_revision:
                raise _integrity_error(
                    'Filesystem checkpoint store detected a record index mismatch.',
                    code='CHECKPOINT_STORE_RECORD_INDEX_MISMATCH',
                )
            self._verify_hard_link_pair(self._by_id_path(stream_key, pending.checkpoint_id), self._by_revision_path(stream_key, pending.revision), purpose='record')
            if by_id.checkpoint_id != pending.checkpoint_id or by_id.revision != pending.revision or by_id.parent_checkpoint_id != pending.parent_checkpoint_id:
                raise _integrity_error(
                    'Filesystem checkpoint store detected a pending/record mismatch.',
                    code='CHECKPOINT_STORE_PENDING_RECORD_MISMATCH',
                )
            if head is None or head.revision < by_id.revision or head.checkpoint_id != by_id.checkpoint_id:
                head = _StreamHead(
                    run_id=by_id.run_id,
                    checkpoint_namespace=by_id.checkpoint_namespace,
                    checkpoint_id=by_id.checkpoint_id,
                    revision=by_id.revision,
                    record_digest=_record_digest(_safe_record_payload(by_id)),
                )
                self._write_head(stream_key, head)
                self._fsync_directory(self._head_path(stream_key).parent)
            elif head.revision > by_id.revision:
                raise _integrity_error(
                    'Filesystem checkpoint store detected an impossible pending transaction.',
                    code='CHECKPOINT_STORE_IMPOSSIBLE_PENDING',
                )
            self._cleanup_path(self._pending_path(stream_key))
            self._validate_committed_chain(stream_key, self._load_head(stream_key) or head, verify_body=verify_body)
            return

    def save(self, request: CheckpointWriteRequest) -> StoredCheckpoint:
        if not isinstance(request, CheckpointWriteRequest):
            raise TypeError('request must be a CheckpointWriteRequest')

        stream_key = self._stream_key(request.run_id, request.checkpoint_namespace)
        body_digest = _sha256_digest(request.body)
        descriptor_revision: int

        with self._locked_stream(stream_key):
            self._recover_stream(stream_key, verify_body=True)

            existing = self._load_record_by_id(stream_key, request.checkpoint_id, verify_body=True)
            if existing is not None:
                if self._same_canonical_request(existing, request):
                    return StoredCheckpoint(
                        run_id=existing.run_id,
                        checkpoint_namespace=existing.checkpoint_namespace,
                        checkpoint_id=existing.checkpoint_id,
                        parent_checkpoint_id=existing.parent_checkpoint_id,
                        revision=existing.revision,
                        serializer_name=existing.serializer_name,
                        serializer_version=existing.serializer_version,
                        content_type=existing.content_type,
                        size=existing.size,
                        digest=existing.digest,
                        metadata=deepcopy(dict(existing.metadata)),
                    )
                raise _conflict_error(
                    'Checkpoint identity conflicts with an existing immutable version.',
                    code='CHECKPOINT_STORE_CONFLICT',
                )

            head = self._load_head(stream_key)
            if head is None:
                if request.parent_checkpoint_id is not None:
                    raise _conflict_error(
                        'Checkpoint write conflicts with the current stream head.',
                        code='CHECKPOINT_STORE_STALE_PARENT',
                    )
                descriptor_revision = 1
            else:
                if request.parent_checkpoint_id != head.checkpoint_id:
                    raise _conflict_error(
                        'Checkpoint write conflicts with the current stream head.',
                        code='CHECKPOINT_STORE_STALE_PARENT',
                    )
                descriptor_revision = head.revision + 1

            descriptor = self._checkpoint_descriptor(request, revision=descriptor_revision)
            record_digest = _record_digest(_safe_record_payload(descriptor))
            pending = _PendingIntent(
                run_id=descriptor.run_id,
                checkpoint_namespace=descriptor.checkpoint_namespace,
                checkpoint_id=descriptor.checkpoint_id,
                parent_checkpoint_id=descriptor.parent_checkpoint_id,
                revision=descriptor.revision,
                body_digest=body_digest,
                record_digest=record_digest,
            )

            body_path = self._body_path(descriptor.digest)
            if not self._publish_immutable_bytes(body_path, request.body).created:
                existing_body = self._read_regular_file_bytes(body_path, purpose='body', max_bytes=descriptor.size, missing_ok=False)
                if existing_body is None or existing_body != request.body:
                    raise _integrity_error(
                        'Filesystem checkpoint store detected a body integrity failure.',
                        code='CHECKPOINT_STORE_BODY_INTEGRITY_FAILURE',
                    )

            self._write_pending(stream_key, pending)

            record_payload = _safe_record_payload(descriptor)
            record_payload['record_digest'] = record_digest
            record_temp = self._write_temp_bytes(self._stream_dir(stream_key) / 'records', _json_bytes(record_payload), suffix='.json')
            try:
                by_id_path = self._by_id_path(stream_key, descriptor.checkpoint_id)
                by_revision_path = self._by_revision_path(stream_key, descriptor.revision)
                if not self._publish_immutable_link(record_temp, by_id_path):
                    existing_record = self._load_record_by_id(stream_key, descriptor.checkpoint_id, verify_body=True)
                    if existing_record is None or existing_record != descriptor:
                        raise _conflict_error(
                            'Checkpoint identity conflicts with an existing immutable version.',
                            code='CHECKPOINT_STORE_CONFLICT',
                        )
                    if self._load_record_by_revision(stream_key, descriptor.revision, verify_body=True) is None:
                        self._publish_immutable_link(by_id_path, by_revision_path)
                        self._fsync_directory(by_revision_path.parent)
                    self._verify_hard_link_pair(by_id_path, by_revision_path, purpose='record')
                    if self._load_head(stream_key) is None or self._load_head(stream_key).revision < descriptor.revision:
                        self._write_head(
                            stream_key,
                            _StreamHead(
                                run_id=descriptor.run_id,
                                checkpoint_namespace=descriptor.checkpoint_namespace,
                                checkpoint_id=descriptor.checkpoint_id,
                                revision=descriptor.revision,
                                record_digest=record_digest,
                            ),
                        )
                    self._cleanup_path(self._pending_path(stream_key))
                    return StoredCheckpoint(
                        run_id=existing_record.run_id,
                        checkpoint_namespace=existing_record.checkpoint_namespace,
                        checkpoint_id=existing_record.checkpoint_id,
                        parent_checkpoint_id=existing_record.parent_checkpoint_id,
                        revision=existing_record.revision,
                        serializer_name=existing_record.serializer_name,
                        serializer_version=existing_record.serializer_version,
                        content_type=existing_record.content_type,
                        size=existing_record.size,
                        digest=existing_record.digest,
                        metadata=deepcopy(dict(existing_record.metadata)),
                    )
                if not self._publish_immutable_link(record_temp, by_revision_path):
                    existing_record = self._load_record_by_revision(stream_key, descriptor.revision, verify_body=True)
                    if existing_record is None or existing_record != descriptor:
                        raise _conflict_error(
                            'Checkpoint identity conflicts with an existing immutable version.',
                            code='CHECKPOINT_STORE_CONFLICT',
                        )
                    self._verify_hard_link_pair(by_id_path, by_revision_path, purpose='record')
                self._fsync_directory(by_id_path.parent)
                self._fsync_directory(by_revision_path.parent)
                self._write_head(
                    stream_key,
                    _StreamHead(
                        run_id=descriptor.run_id,
                        checkpoint_namespace=descriptor.checkpoint_namespace,
                        checkpoint_id=descriptor.checkpoint_id,
                        revision=descriptor.revision,
                        record_digest=record_digest,
                    ),
                )
                self._cleanup_path(self._pending_path(stream_key))
            finally:
                self._cleanup_path(record_temp)

            return StoredCheckpoint(
                run_id=descriptor.run_id,
                checkpoint_namespace=descriptor.checkpoint_namespace,
                checkpoint_id=descriptor.checkpoint_id,
                parent_checkpoint_id=descriptor.parent_checkpoint_id,
                revision=descriptor.revision,
                serializer_name=descriptor.serializer_name,
                serializer_version=descriptor.serializer_version,
                content_type=descriptor.content_type,
                size=descriptor.size,
                digest=descriptor.digest,
                metadata=deepcopy(dict(descriptor.metadata)),
            )

    def load_latest(self, run_id: int | str, *, checkpoint_namespace: str = '') -> CheckpointReadResult | None:
        stream_key = self._stream_key(run_id, checkpoint_namespace)
        with self._locked_stream(stream_key):
            self._recover_stream(stream_key, verify_body=True)
            head = self._load_head(stream_key)
            if head is None:
                return None
            record = self._load_record_by_revision(stream_key, head.revision, verify_body=True)
            if record is None:
                raise _integrity_error(
                    'Filesystem checkpoint store detected a missing head record.',
                    code='CHECKPOINT_STORE_MISSING_HEAD_RECORD',
                )
            if record.checkpoint_id != head.checkpoint_id or _record_digest(_safe_record_payload(record)) != head.record_digest:
                raise _integrity_error(
                    'Filesystem checkpoint store detected a head mismatch.',
                    code='CHECKPOINT_STORE_HEAD_MISMATCH',
                )
            self._verify_hard_link_pair(self._by_id_path(stream_key, record.checkpoint_id), self._by_revision_path(stream_key, head.revision), purpose='record')
            return CheckpointReadResult(
                checkpoint=StoredCheckpoint(
                    run_id=record.run_id,
                    checkpoint_namespace=record.checkpoint_namespace,
                    checkpoint_id=record.checkpoint_id,
                    parent_checkpoint_id=record.parent_checkpoint_id,
                    revision=record.revision,
                    serializer_name=record.serializer_name,
                    serializer_version=record.serializer_version,
                    content_type=record.content_type,
                    size=record.size,
                    digest=record.digest,
                    metadata=deepcopy(dict(record.metadata)),
                ),
                body=self._read_regular_file_bytes(self._body_path(record.digest), purpose='body', max_bytes=record.size, missing_ok=False) or b'',
            )

    def load_checkpoint(self, run_id: int | str, checkpoint_id: str, *, checkpoint_namespace: str = '') -> CheckpointReadResult | None:
        stream_key = self._stream_key(run_id, checkpoint_namespace)
        normalized_checkpoint_id = normalize_checkpoint_id(checkpoint_id)
        with self._locked_stream(stream_key):
            self._recover_stream(stream_key, verify_body=True)
            head = self._load_head(stream_key)
            if head is None:
                return None
            record = self._load_record_by_id(stream_key, normalized_checkpoint_id, verify_body=True)
            if record is None:
                return None
            if record.revision > head.revision:
                raise _integrity_error(
                    'Filesystem checkpoint store detected a head mismatch.',
                    code='CHECKPOINT_STORE_HEAD_MISMATCH',
                )
            if _record_digest(_safe_record_payload(record)) != head.record_digest and record.revision == head.revision:
                raise _integrity_error(
                    'Filesystem checkpoint store detected a head digest mismatch.',
                    code='CHECKPOINT_STORE_HEAD_DIGEST_MISMATCH',
                )
            self._verify_hard_link_pair(self._by_id_path(stream_key, record.checkpoint_id), self._by_revision_path(stream_key, record.revision), purpose='record')
            return CheckpointReadResult(
                checkpoint=StoredCheckpoint(
                    run_id=record.run_id,
                    checkpoint_namespace=record.checkpoint_namespace,
                    checkpoint_id=record.checkpoint_id,
                    parent_checkpoint_id=record.parent_checkpoint_id,
                    revision=record.revision,
                    serializer_name=record.serializer_name,
                    serializer_version=record.serializer_version,
                    content_type=record.content_type,
                    size=record.size,
                    digest=record.digest,
                    metadata=deepcopy(dict(record.metadata)),
                ),
                body=self._read_regular_file_bytes(self._body_path(record.digest), purpose='body', max_bytes=record.size, missing_ok=False) or b'',
            )

    def list_for_run(self, run_id: int | str, *, checkpoint_namespace: str = '') -> list[StoredCheckpoint]:
        stream_key = self._stream_key(run_id, checkpoint_namespace)
        with self._locked_stream(stream_key):
            self._recover_stream(stream_key, verify_body=False)
            head = self._load_head(stream_key)
            if head is None:
                return []
            committed = self._validate_committed_chain(stream_key, head, verify_body=False)
            self._audit_no_extra_finalized_records(stream_key, committed)
            descriptors: list[StoredCheckpoint] = []
            for revision in range(1, head.revision + 1):
                record = self._load_record_by_revision(stream_key, revision, verify_body=False)
                if record is None:
                    raise _integrity_error(
                        'Filesystem checkpoint store detected a revision gap.',
                        code='CHECKPOINT_STORE_REVISION_GAP',
                    )
                self._validate_listing_body(record)
                descriptors.append(
                    StoredCheckpoint(
                        run_id=record.run_id,
                        checkpoint_namespace=record.checkpoint_namespace,
                        checkpoint_id=record.checkpoint_id,
                        parent_checkpoint_id=record.parent_checkpoint_id,
                        revision=record.revision,
                        serializer_name=record.serializer_name,
                        serializer_version=record.serializer_version,
                        content_type=record.content_type,
                        size=record.size,
                        digest=record.digest,
                        metadata=deepcopy(dict(record.metadata)),
                    )
                )
            return descriptors

    def _validate_listing_body(self, descriptor: StoredCheckpoint) -> None:
        body_path = self._body_path(descriptor.digest)
        if body_path.is_symlink():
            raise _integrity_error(
                'Filesystem checkpoint store detected a body symlink.',
                code='CHECKPOINT_STORE_BODY_SYMLINK',
            )
        try:
            st = body_path.lstat()
        except FileNotFoundError:
            raise _integrity_error(
                'Filesystem checkpoint store detected a missing body.',
                code='CHECKPOINT_STORE_MISSING_BODY',
            ) from None
        except OSError as exc:
            raise _persistence_error(
                'Filesystem checkpoint store failed while inspecting a body.',
                code='CHECKPOINT_STORE_BODY_STAT_FAILED',
            ) from exc
        if not stat.S_ISREG(st.st_mode):
            raise _integrity_error(
                'Filesystem checkpoint store detected a non-regular body.',
                code='CHECKPOINT_STORE_NONREGULAR_BODY',
            )
        if st.st_size != descriptor.size:
            raise _integrity_error(
                'Filesystem checkpoint store detected a body size mismatch.',
                code='CHECKPOINT_STORE_BODY_SIZE_MISMATCH',
            )
