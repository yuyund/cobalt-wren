"""Process-durable filesystem artifact store."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import uuid
from collections.abc import Iterable
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from langgraph_automation.api.errors import ArtifactConflictError, ArtifactIntegrityError, ArtifactPersistenceError, ArtifactValidationError

from .base import (
    ArtifactReadResult,
    ArtifactStore,
    ArtifactWriteRequest,
    StoredArtifact,
    normalize_artifact_body,
    normalize_artifact_content_type,
    normalize_artifact_kind,
    normalize_artifact_metadata,
    normalize_artifact_name,
    normalize_artifact_run_id,
    normalize_artifact_storage_key,
)

__all__ = ['FilesystemArtifactStore']

_ARTIFACT_COMPONENT = 'artifact_store'
_SCHEMA_VERSION = 1
_MAX_MANIFEST_BYTES = 1 << 20
_MANIFEST_FILENAME_RE = re.compile(r'^[0-9a-f]{64}\.json$')


@dataclass(frozen=True, slots=True)
class _PublishedBytes:
    created: bool
    path: Path


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_digest(data: bytes) -> str:
    return f'sha256:{_sha256_hex(data)}'


def _storage_key_digest(storage_key: str) -> str:
    return _sha256_hex(storage_key.encode('utf-8'))


def _safe_reference(storage_key: str) -> str:
    return _storage_key_digest(storage_key)[:12]


def _digest_suffix(digest: str) -> str:
    if not digest.startswith('sha256:'):
        raise ArtifactIntegrityError(
            'Filesystem artifact store recorded an invalid digest.',
            code='ARTIFACT_STORE_INVALID_DIGEST',
            component=_ARTIFACT_COMPONENT,
        )
    return digest.split(':', 1)[1]


def _manifest_payload(artifact: StoredArtifact) -> dict[str, Any]:
    return {
        'schema_version': _SCHEMA_VERSION,
        'run_id': artifact.run_id,
        'storage_key': artifact.storage_key,
        'name': artifact.name,
        'kind': artifact.kind,
        'content_type': artifact.content_type,
        'size': artifact.size,
        'digest': artifact.digest,
        'metadata': artifact.metadata,
    }


def _encode_manifest(artifact: StoredArtifact) -> bytes:
    return json.dumps(
        _manifest_payload(artifact),
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


def _decode_manifest(data: bytes) -> dict[str, Any]:
    if len(data) > _MAX_MANIFEST_BYTES:
        raise ValueError('manifest too large')

    def _parse_constant(_: str) -> None:
        raise ValueError('invalid JSON constant')

    parsed = json.loads(
        data.decode('utf-8'),
        object_pairs_hook=_reject_duplicate_keys,
        parse_constant=_parse_constant,
    )
    if not isinstance(parsed, dict):
        raise ValueError('manifest must be a JSON object')
    return parsed


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


def _clone_read_result(result: ArtifactReadResult) -> ArtifactReadResult:
    return ArtifactReadResult(artifact=_clone_artifact(result.artifact), body=bytes(result.body))


class FilesystemArtifactStore(ArtifactStore):
    """Process-durable artifact store backed by immutable filesystem records."""

    def __init__(self, root: str | os.PathLike[str]) -> None:
        root_path = Path(root).expanduser()
        if not root_path.is_absolute():
            raise ArtifactValidationError(
                'Filesystem artifact store requires an absolute root path.',
                code='ARTIFACT_STORE_INVALID_ROOT',
                component=_ARTIFACT_COMPONENT,
            )
        self._root = root_path
        self._ensure_root_directory()
        self._ensure_directory_chain(('bodies', 'sha256'))
        self._ensure_directory_chain(('records', 'sha256'))

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(root=<trusted>)'

    def put(self, request: ArtifactWriteRequest) -> StoredArtifact:
        try:
            storage_key = normalize_artifact_storage_key(request.storage_key)
        except ValueError:
            raise ArtifactValidationError(
                'Artifact store rejected an invalid storage key.',
                code='ARTIFACT_STORE_INVALID_STORAGE_KEY',
                component=_ARTIFACT_COMPONENT,
            ) from None
        run_id = normalize_artifact_run_id(request.run_id)
        body = normalize_artifact_body(request.body)
        name = normalize_artifact_name(request.name) if request.name else ''
        kind = normalize_artifact_kind(request.kind) if request.kind else ''
        content_type = normalize_artifact_content_type(request.content_type)
        metadata = normalize_artifact_metadata(request.metadata)

        digest = _sha256_digest(body)
        artifact = StoredArtifact(
            run_id=run_id,
            storage_key=storage_key,
            name=name,
            kind=kind,
            content_type=content_type,
            size=len(body),
            digest=digest,
            metadata=metadata,
        )

        existing = self._load_existing_artifact(storage_key)
        if existing is not None:
            if existing.artifact == artifact and existing.body == body:
                return _clone_artifact(existing.artifact)
            if existing.artifact == artifact and existing.body != body:
                raise self._integrity_error(
                    'Filesystem artifact store detected a body integrity failure.',
                    storage_key=storage_key,
                    code='ARTIFACT_STORE_BODY_INTEGRITY_FAILURE',
                )
            raise self._conflict_error('Filesystem artifact store detected a write conflict.', storage_key=storage_key)

        body_path = self._body_path_for_digest(digest)
        self._ensure_directory_chain(('bodies', 'sha256', body_path.parent.parent.name, body_path.parent.name))
        published_body = self._publish_immutable_bytes(body_path, body)
        if not published_body.created:
            existing_body = self._read_regular_file_bytes(
                body_path,
                purpose='body',
                storage_key=storage_key,
                max_bytes=len(body) + 1,
            )
            if existing_body != body:
                raise self._integrity_error(
                    'Filesystem artifact store detected a body integrity failure.',
                    storage_key=storage_key,
                    code='ARTIFACT_STORE_BODY_INTEGRITY_FAILURE',
                )

        manifest_bytes = _encode_manifest(artifact)
        manifest_path = self._manifest_path_for_storage_key(storage_key)
        self._ensure_directory_chain(('records', 'sha256', manifest_path.parent.parent.name, manifest_path.parent.name))
        published_manifest = self._publish_immutable_bytes(manifest_path, manifest_bytes)
        if not published_manifest.created:
            existing_manifest = self._load_existing_artifact(storage_key)
            if existing_manifest is None:
                raise self._integrity_error(
                    'Filesystem artifact store detected a missing manifest after publication.',
                    storage_key=storage_key,
                    code='ARTIFACT_STORE_MISSING_MANIFEST',
                )
            if existing_manifest.artifact == artifact:
                return _clone_artifact(existing_manifest.artifact)
            raise self._conflict_error('Filesystem artifact store detected a write conflict.', storage_key=storage_key)
        return _clone_artifact(artifact)

    def get(self, storage_key: str) -> ArtifactReadResult | None:
        try:
            normalized_key = normalize_artifact_storage_key(storage_key)
        except ValueError:
            raise ArtifactValidationError(
                'Artifact store rejected an invalid storage key.',
                code='ARTIFACT_STORE_INVALID_STORAGE_KEY',
                component=_ARTIFACT_COMPONENT,
            ) from None
        record_path = self._manifest_path_for_storage_key(normalized_key)
        manifest_bytes = self._read_regular_file_bytes(
            record_path,
            purpose='manifest',
            storage_key=normalized_key,
            max_bytes=_MAX_MANIFEST_BYTES,
            missing_ok=True,
        )
        if manifest_bytes is None:
            return None
        artifact = self._artifact_from_manifest_bytes(
            manifest_bytes,
            record_path=record_path,
            record_digest=_storage_key_digest(normalized_key),
            storage_key=normalized_key,
        )
        body_path = self._body_path_for_digest(artifact.digest)
        body = self._read_body_for_digest(body_path, artifact.digest, artifact.size, storage_key=normalized_key)
        return _clone_read_result(ArtifactReadResult(artifact=artifact, body=body))

    def list_for_run(self, run_id: int | str) -> list[StoredArtifact]:
        normalized_run_id = normalize_artifact_run_id(run_id)
        records_root = self._root / 'records' / 'sha256'
        if not records_root.exists():
            return []

        artifacts: list[StoredArtifact] = []
        for path in sorted(records_root.rglob('*.json')):
            if not _MANIFEST_FILENAME_RE.fullmatch(path.name):
                continue
            artifact = self._artifact_from_manifest_path(path)
            if artifact.run_id != normalized_run_id:
                continue
            body_path = self._body_path_for_digest(artifact.digest)
            self._validate_body_entry_metadata(body_path, artifact.size, storage_key=artifact.storage_key)
            artifacts.append(_clone_artifact(artifact))

        return sorted(artifacts, key=lambda item: item.storage_key)

    def _ensure_root_directory(self) -> None:
        self._ensure_directory(self._root)

    def _ensure_directory_chain(self, relative_parts: tuple[str, ...]) -> Path:
        current = self._root
        for part in relative_parts:
            current = current / part
            self._ensure_directory(current)
        return current

    def _ensure_directory(self, path: Path) -> None:
        try:
            path.mkdir(parents=True, exist_ok=True)
            st = path.lstat()
            if stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode):
                raise ArtifactPersistenceError(
                    'Filesystem artifact store root is unavailable.',
                    code='ARTIFACT_STORE_DIRECTORY_UNAVAILABLE',
                    component=_ARTIFACT_COMPONENT,
                )
        except ArtifactPersistenceError:
            raise
        except OSError:
            raise ArtifactPersistenceError(
                'Filesystem artifact store root is unavailable.',
                code='ARTIFACT_STORE_DIRECTORY_UNAVAILABLE',
                component=_ARTIFACT_COMPONENT,
            ) from None

    def _body_path_for_digest(self, digest: str) -> Path:
        suffix = _digest_suffix(digest)
        return self._root / 'bodies' / 'sha256' / suffix[:2] / suffix[2:4] / f'{suffix}.blob'

    def _manifest_path_for_storage_key(self, storage_key: str) -> Path:
        digest = _storage_key_digest(storage_key)
        return self._root / 'records' / 'sha256' / digest[:2] / digest[2:4] / f'{digest}.json'

    def _publish_immutable_bytes(self, final_path: Path, payload: bytes) -> _PublishedBytes:
        self._ensure_directory_chain(tuple(final_path.parent.relative_to(self._root).parts))
        temp_name = f'.tmp-{uuid.uuid4().hex}'
        temp_path = final_path.parent / temp_name
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
        if hasattr(os, 'O_CLOEXEC'):
            flags |= os.O_CLOEXEC
        mode = 0o600
        fd: int | None = None
        try:
            fd = os.open(temp_path, flags, mode)
            try:
                view = memoryview(payload)
                total = 0
                while total < len(view):
                    written = os.write(fd, view[total:])
                    if written == 0:
                        raise ArtifactPersistenceError(
                            'Filesystem artifact write failed.',
                            code='ARTIFACT_STORE_WRITE_FAILED',
                            component=_ARTIFACT_COMPONENT,
                        )
                    total += written
                os.fsync(fd)
            finally:
                os.close(fd)
                fd = None
            try:
                os.link(temp_path, final_path)
            except FileExistsError:
                return _PublishedBytes(created=False, path=final_path)
            except OSError:
                raise ArtifactPersistenceError(
                    'Filesystem artifact publication is unsupported on this filesystem.',
                    code='ARTIFACT_STORE_PUBLICATION_UNSUPPORTED',
                    component=_ARTIFACT_COMPONENT,
                ) from None
            return _PublishedBytes(created=True, path=final_path)
        except ArtifactPersistenceError:
            raise
        except OSError:
            raise ArtifactPersistenceError(
                'Filesystem artifact write failed.',
                code='ARTIFACT_STORE_WRITE_FAILED',
                component=_ARTIFACT_COMPONENT,
            ) from None
        finally:
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
            try:
                if temp_path.exists():
                    temp_path.unlink()
            except OSError:
                pass

    def _artifact_from_manifest_path(self, path: Path) -> StoredArtifact:
        manifest_bytes = self._read_regular_file_bytes(
            path,
            purpose='manifest',
            storage_key=path.stem,
            max_bytes=_MAX_MANIFEST_BYTES,
        )
        if manifest_bytes is None:
            raise self._integrity_error(
                'Filesystem artifact store detected a missing manifest.',
                storage_key=path.stem,
                code='ARTIFACT_STORE_MISSING_MANIFEST',
            )
        return self._artifact_from_manifest_bytes(
            manifest_bytes,
            record_path=path,
            record_digest=path.stem,
            storage_key=path.stem,
        )

    def _artifact_from_manifest_bytes(self, manifest_bytes: bytes, *, record_path: Path, record_digest: str, storage_key: str) -> StoredArtifact:
        try:
            payload = _decode_manifest(manifest_bytes)
        except (UnicodeDecodeError, ValueError):
            raise self._integrity_error(
                'Filesystem artifact store detected an invalid manifest.',
                storage_key=storage_key,
                code='ARTIFACT_STORE_INVALID_MANIFEST',
            ) from None

        required_keys = {
            'schema_version',
            'run_id',
            'storage_key',
            'name',
            'kind',
            'content_type',
            'size',
            'digest',
            'metadata',
        }
        if set(payload) != required_keys:
            raise self._integrity_error(
                'Filesystem artifact store detected an invalid manifest.',
                storage_key=storage_key,
                code='ARTIFACT_STORE_INVALID_MANIFEST',
            )
        if payload['schema_version'] != _SCHEMA_VERSION:
            raise self._integrity_error(
                'Filesystem artifact store detected an unsupported manifest schema.',
                storage_key=storage_key,
                code='ARTIFACT_STORE_UNSUPPORTED_SCHEMA',
            )

        manifest_storage_key = normalize_artifact_storage_key(payload['storage_key'])
        if _storage_key_digest(manifest_storage_key) != record_digest:
            raise self._integrity_error(
                'Filesystem artifact store detected a manifest mapping mismatch.',
                storage_key=storage_key,
                code='ARTIFACT_STORE_MANIFEST_KEY_MISMATCH',
            )

        try:
            artifact = StoredArtifact(
                run_id=normalize_artifact_run_id(payload['run_id']),
                storage_key=manifest_storage_key,
                name=normalize_artifact_name(payload['name']) if payload['name'] else '',
                kind=normalize_artifact_kind(payload['kind']) if payload['kind'] else '',
                content_type=normalize_artifact_content_type(payload['content_type']),
                size=payload['size'],
                digest=payload['digest'],
                metadata=normalize_artifact_metadata(payload['metadata']),
            )
        except ArtifactIntegrityError:
            raise self._integrity_error(
                'Filesystem artifact store detected an invalid manifest.',
                storage_key=storage_key,
                code='ARTIFACT_STORE_INVALID_MANIFEST',
            ) from None
        except ArtifactValidationError:
            raise self._integrity_error(
                'Filesystem artifact store detected an invalid manifest.',
                storage_key=storage_key,
                code='ARTIFACT_STORE_INVALID_MANIFEST',
            ) from None

        canonical_bytes = _encode_manifest(artifact)
        if canonical_bytes != manifest_bytes:
            raise self._integrity_error(
                'Filesystem artifact store detected a noncanonical manifest.',
                storage_key=storage_key,
                code='ARTIFACT_STORE_NONCANONICAL_MANIFEST',
            )
        return artifact

    def _load_existing_artifact(self, storage_key: str) -> ArtifactReadResult | None:
        record_path = self._manifest_path_for_storage_key(storage_key)
        manifest_bytes = self._read_regular_file_bytes(
            record_path,
            purpose='manifest',
            storage_key=storage_key,
            max_bytes=_MAX_MANIFEST_BYTES,
            missing_ok=True,
        )
        if manifest_bytes is None:
            return None
        artifact = self._artifact_from_manifest_bytes(
            manifest_bytes,
            record_path=record_path,
            record_digest=_storage_key_digest(storage_key),
            storage_key=storage_key,
        )
        body_path = self._body_path_for_digest(artifact.digest)
        body = self._read_body_for_digest(body_path, artifact.digest, artifact.size, storage_key=storage_key)
        return ArtifactReadResult(artifact=artifact, body=body)

    def _read_body_for_digest(self, body_path: Path, digest: str, expected_size: int, *, storage_key: str) -> bytes:
        body = self._read_regular_file_bytes(
            body_path,
            purpose='body',
            storage_key=storage_key,
            max_bytes=None,
        )
        if body is None:
            raise self._integrity_error(
                'Filesystem artifact store detected a missing body.',
                storage_key=storage_key,
                code='ARTIFACT_STORE_MISSING_BODY',
            )
        if len(body) != expected_size:
            raise self._integrity_error(
                'Filesystem artifact store detected a body size mismatch.',
                storage_key=storage_key,
                code='ARTIFACT_STORE_SIZE_MISMATCH',
            )
        self._verify_body_bytes(body, digest, storage_key=storage_key)
        return body

    def _validate_body_entry_metadata(self, body_path: Path, expected_size: int, *, storage_key: str) -> None:
        if body_path.is_symlink():
            raise self._integrity_error(
                'Filesystem artifact store detected a body symlink.',
                storage_key=storage_key,
                code='ARTIFACT_STORE_SYMLINK',
            )
        flags = os.O_RDONLY
        if hasattr(os, 'O_CLOEXEC'):
            flags |= os.O_CLOEXEC
        if hasattr(os, 'O_NOFOLLOW'):
            flags |= os.O_NOFOLLOW
        try:
            fd = os.open(body_path, flags)
        except FileNotFoundError:
            raise self._integrity_error(
                'Filesystem artifact store detected a missing body.',
                storage_key=storage_key,
                code='ARTIFACT_STORE_MISSING_BODY',
            ) from None
        except OSError:
            raise ArtifactPersistenceError(
                'Filesystem artifact read failed.',
                code='ARTIFACT_STORE_READ_FAILED',
                component=_ARTIFACT_COMPONENT,
            ) from None

        try:
            try:
                st = os.fstat(fd)
            except OSError:
                raise ArtifactPersistenceError(
                    'Filesystem artifact read failed.',
                    code='ARTIFACT_STORE_READ_FAILED',
                    component=_ARTIFACT_COMPONENT,
                ) from None
            if not stat.S_ISREG(st.st_mode):
                raise self._integrity_error(
                    'Filesystem artifact store detected a non-regular body.',
                    storage_key=storage_key,
                    code='ARTIFACT_STORE_NONREGULAR_BODY',
                )
            if st.st_size != expected_size:
                raise self._integrity_error(
                    'Filesystem artifact store detected a body size mismatch.',
                    storage_key=storage_key,
                    code='ARTIFACT_STORE_SIZE_MISMATCH',
                )
        finally:
            try:
                os.close(fd)
            except OSError:
                pass

    def _verify_body_bytes(self, body: bytes, digest: str, *, storage_key: str) -> None:
        if _sha256_digest(body) != digest:
            raise self._integrity_error(
                'Filesystem artifact store detected a body digest mismatch.',
                storage_key=storage_key,
                code='ARTIFACT_STORE_DIGEST_MISMATCH',
            )

    def _read_regular_file_bytes(
        self,
        path: Path,
        *,
        purpose: str,
        storage_key: str,
        max_bytes: int | None,
        missing_ok: bool = False,
    ) -> bytes | None:
        if hasattr(os, 'O_NOFOLLOW') and path.is_symlink():
            raise self._integrity_error(
                f'Filesystem artifact store detected a {purpose} symlink.',
                storage_key=storage_key,
                code='ARTIFACT_STORE_SYMLINK',
            )
        flags = os.O_RDONLY
        if hasattr(os, 'O_CLOEXEC'):
            flags |= os.O_CLOEXEC
        if hasattr(os, 'O_NOFOLLOW'):
            flags |= os.O_NOFOLLOW
        try:
            fd = os.open(path, flags)
        except FileNotFoundError:
            if missing_ok:
                return None
            raise self._integrity_error(
                f'Filesystem artifact store detected a missing {purpose}.',
                storage_key=storage_key,
                code=f'ARTIFACT_STORE_MISSING_{purpose.upper()}',
            ) from None
        except OSError:
            raise ArtifactPersistenceError(
                'Filesystem artifact read failed.',
                code='ARTIFACT_STORE_READ_FAILED',
                component=_ARTIFACT_COMPONENT,
            ) from None

        try:
            try:
                st = os.fstat(fd)
            except OSError:
                raise ArtifactPersistenceError(
                    'Filesystem artifact read failed.',
                    code='ARTIFACT_STORE_READ_FAILED',
                    component=_ARTIFACT_COMPONENT,
                ) from None
            if not stat.S_ISREG(st.st_mode):
                raise self._integrity_error(
                    f'Filesystem artifact store detected a non-regular {purpose}.',
                    storage_key=storage_key,
                    code=f'ARTIFACT_STORE_NONREGULAR_{purpose.upper()}',
                )
            chunks: list[bytes] = []
            total = 0
            while True:
                try:
                    chunk = os.read(fd, 8192)
                except OSError:
                    raise ArtifactPersistenceError(
                        'Filesystem artifact read failed.',
                        code='ARTIFACT_STORE_READ_FAILED',
                        component=_ARTIFACT_COMPONENT,
                    ) from None
                if not chunk:
                    break
                total += len(chunk)
                if max_bytes is not None and total > max_bytes:
                    raise self._integrity_error(
                        f'Filesystem artifact store detected an oversized {purpose}.',
                        storage_key=storage_key,
                        code=f'ARTIFACT_STORE_OVERSIZED_{purpose.upper()}',
                    )
                chunks.append(chunk)
            return b''.join(chunks)
        finally:
            try:
                os.close(fd)
            except OSError:
                pass

    def _conflict_error(self, safe_message: str, *, storage_key: str) -> ArtifactConflictError:
        return ArtifactConflictError(
            f'{safe_message} Reference {_safe_reference(storage_key)}.',
            code='ARTIFACT_STORE_WRITE_CONFLICT',
            component=_ARTIFACT_COMPONENT,
            metadata={'reference': _safe_reference(storage_key)},
        )

    def _integrity_error(self, safe_message: str, *, storage_key: str, code: str) -> ArtifactIntegrityError:
        return ArtifactIntegrityError(
            f'{safe_message} Reference {_safe_reference(storage_key)}.',
            code=code,
            component=_ARTIFACT_COMPONENT,
            metadata={'reference': _safe_reference(storage_key)},
        )
