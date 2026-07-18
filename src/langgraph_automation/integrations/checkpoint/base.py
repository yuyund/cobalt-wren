"""Checkpoint store interfaces and versioned checkpoint value types."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from types import MappingProxyType
from typing import Any, Mapping, Protocol, runtime_checkable
import re

from langgraph_automation.api.errors import (
    CheckpointIntegrityError,
    CheckpointValidationError,
)

__all__ = [
    'CheckpointStore',
    'CheckpointWriteRequest',
    'StoredCheckpoint',
    'CheckpointReadResult',
]

_CHECKPOINT_COMPONENT = 'checkpoint_store'
_MAX_IDENTIFIER_LENGTH = 255
_MAX_METADATA_DEPTH = 16
_MAX_METADATA_ITEMS = 1000
_MAX_METADATA_STRING_LENGTH = 65_536
_SERIALIZER_NAME_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]*$')
_CHECKPOINT_ID_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:-]*$')


def _raise_validation(message: str, *, code: str) -> CheckpointValidationError:
    return CheckpointValidationError(message, code=code, component=_CHECKPOINT_COMPONENT)


def normalize_checkpoint_run_id(run_id: int | str) -> int | str:
    """Return a normalized execution run identifier."""

    if isinstance(run_id, bool) or not isinstance(run_id, (int, str)):
        raise _raise_validation('Checkpoint store rejected an invalid run identifier.', code='CHECKPOINT_STORE_INVALID_RUN_ID')
    if isinstance(run_id, str):
        normalized = run_id.strip()
        if not normalized or len(normalized) > _MAX_IDENTIFIER_LENGTH:
            raise _raise_validation('Checkpoint store rejected an invalid run identifier.', code='CHECKPOINT_STORE_INVALID_RUN_ID')
        return normalized
    return run_id


def normalize_checkpoint_namespace(checkpoint_namespace: str) -> str:
    """Return a normalized checkpoint namespace."""

    if not isinstance(checkpoint_namespace, str):
        raise _raise_validation('Checkpoint store rejected an invalid checkpoint namespace.', code='CHECKPOINT_STORE_INVALID_NAMESPACE')
    if checkpoint_namespace != checkpoint_namespace.strip():
        raise _raise_validation('Checkpoint store rejected an invalid checkpoint namespace.', code='CHECKPOINT_STORE_INVALID_NAMESPACE')
    if not checkpoint_namespace:
        return ''
    if len(checkpoint_namespace) > _MAX_IDENTIFIER_LENGTH or '\x00' in checkpoint_namespace:
        raise _raise_validation('Checkpoint store rejected an invalid checkpoint namespace.', code='CHECKPOINT_STORE_INVALID_NAMESPACE')
    if not _CHECKPOINT_ID_RE.fullmatch(checkpoint_namespace):
        raise _raise_validation('Checkpoint store rejected an invalid checkpoint namespace.', code='CHECKPOINT_STORE_INVALID_NAMESPACE')
    return checkpoint_namespace


def normalize_checkpoint_id(checkpoint_id: str) -> str:
    """Return a normalized checkpoint identifier."""

    if not isinstance(checkpoint_id, str):
        raise _raise_validation('Checkpoint store rejected an invalid checkpoint identifier.', code='CHECKPOINT_STORE_INVALID_CHECKPOINT_ID')
    if checkpoint_id != checkpoint_id.strip():
        raise _raise_validation('Checkpoint store rejected an invalid checkpoint identifier.', code='CHECKPOINT_STORE_INVALID_CHECKPOINT_ID')
    if not checkpoint_id or len(checkpoint_id) > _MAX_IDENTIFIER_LENGTH or '\x00' in checkpoint_id:
        raise _raise_validation('Checkpoint store rejected an invalid checkpoint identifier.', code='CHECKPOINT_STORE_INVALID_CHECKPOINT_ID')
    if not _CHECKPOINT_ID_RE.fullmatch(checkpoint_id):
        raise _raise_validation('Checkpoint store rejected an invalid checkpoint identifier.', code='CHECKPOINT_STORE_INVALID_CHECKPOINT_ID')
    return checkpoint_id


def normalize_checkpoint_serializer_name(serializer_name: str) -> str:
    """Return a normalized serializer identifier."""

    if not isinstance(serializer_name, str):
        raise _raise_validation('Checkpoint store rejected an invalid serializer name.', code='CHECKPOINT_STORE_INVALID_SERIALIZER_NAME')
    if serializer_name != serializer_name.strip():
        raise _raise_validation('Checkpoint store rejected an invalid serializer name.', code='CHECKPOINT_STORE_INVALID_SERIALIZER_NAME')
    if not serializer_name or len(serializer_name) > _MAX_IDENTIFIER_LENGTH or '\x00' in serializer_name:
        raise _raise_validation('Checkpoint store rejected an invalid serializer name.', code='CHECKPOINT_STORE_INVALID_SERIALIZER_NAME')
    if not _SERIALIZER_NAME_RE.fullmatch(serializer_name):
        raise _raise_validation('Checkpoint store rejected an invalid serializer name.', code='CHECKPOINT_STORE_INVALID_SERIALIZER_NAME')
    return serializer_name


def normalize_checkpoint_serializer_version(serializer_version: int) -> int:
    """Return a validated serializer version."""

    if isinstance(serializer_version, bool) or not isinstance(serializer_version, int) or serializer_version <= 0:
        raise _raise_validation('Checkpoint store rejected an invalid serializer version.', code='CHECKPOINT_STORE_INVALID_SERIALIZER_VERSION')
    return serializer_version


def normalize_checkpoint_content_type(content_type: str) -> str:
    """Return a normalized content type."""

    if not isinstance(content_type, str):
        raise _raise_validation('Checkpoint store rejected an invalid content type.', code='CHECKPOINT_STORE_INVALID_CONTENT_TYPE')
    if content_type != content_type.strip():
        raise _raise_validation('Checkpoint store rejected an invalid content type.', code='CHECKPOINT_STORE_INVALID_CONTENT_TYPE')
    normalized = content_type.lower()
    if not normalized or len(normalized) > _MAX_IDENTIFIER_LENGTH or '\x00' in normalized:
        raise _raise_validation('Checkpoint store rejected an invalid content type.', code='CHECKPOINT_STORE_INVALID_CONTENT_TYPE')
    if '/' not in normalized or normalized.count('/') != 1:
        raise _raise_validation('Checkpoint store rejected an invalid content type.', code='CHECKPOINT_STORE_INVALID_CONTENT_TYPE')
    if any(ch.isspace() for ch in normalized):
        raise _raise_validation('Checkpoint store rejected an invalid content type.', code='CHECKPOINT_STORE_INVALID_CONTENT_TYPE')
    return normalized


def normalize_checkpoint_body(body: Any) -> bytes:
    """Return checkpoint body bytes."""

    if not isinstance(body, bytes):
        raise _raise_validation('Checkpoint store rejected an invalid checkpoint body.', code='CHECKPOINT_STORE_INVALID_BODY')
    return body


def _normalize_metadata_value(value: Any, *, depth: int, seen: set[int]) -> Any:
    if depth > _MAX_METADATA_DEPTH:
        raise _raise_validation('Checkpoint store rejected invalid metadata.', code='CHECKPOINT_STORE_INVALID_METADATA')
    if value is None or isinstance(value, bool) or isinstance(value, int):
        return value
    if isinstance(value, float):
        if not isfinite(value):
            raise _raise_validation('Checkpoint store rejected invalid metadata.', code='CHECKPOINT_STORE_INVALID_METADATA')
        return value
    if isinstance(value, str):
        if len(value) > _MAX_METADATA_STRING_LENGTH:
            raise _raise_validation('Checkpoint store rejected invalid metadata.', code='CHECKPOINT_STORE_INVALID_METADATA')
        return value
    if isinstance(value, (bytes, bytearray, memoryview)):
        raise _raise_validation('Checkpoint store rejected invalid metadata.', code='CHECKPOINT_STORE_INVALID_METADATA')
    if isinstance(value, Mapping):
        value_id = id(value)
        if value_id in seen:
            raise _raise_validation('Checkpoint store rejected invalid metadata.', code='CHECKPOINT_STORE_INVALID_METADATA')
        if len(value) > _MAX_METADATA_ITEMS:
            raise _raise_validation('Checkpoint store rejected invalid metadata.', code='CHECKPOINT_STORE_INVALID_METADATA')
        seen.add(value_id)
        try:
            normalized: dict[str, Any] = {}
            for key in value.keys():
                if not isinstance(key, str):
                    raise _raise_validation('Checkpoint store rejected invalid metadata.', code='CHECKPOINT_STORE_INVALID_METADATA')
                if len(key) > _MAX_IDENTIFIER_LENGTH:
                    raise _raise_validation('Checkpoint store rejected invalid metadata.', code='CHECKPOINT_STORE_INVALID_METADATA')
                nested_value = value[key]
                normalized[key] = _normalize_metadata_value(nested_value, depth=depth + 1, seen=seen)
            return normalized
        finally:
            seen.remove(value_id)
    if isinstance(value, list):
        value_id = id(value)
        if value_id in seen:
            raise _raise_validation('Checkpoint store rejected invalid metadata.', code='CHECKPOINT_STORE_INVALID_METADATA')
        if len(value) > _MAX_METADATA_ITEMS:
            raise _raise_validation('Checkpoint store rejected invalid metadata.', code='CHECKPOINT_STORE_INVALID_METADATA')
        seen.add(value_id)
        try:
            return [_normalize_metadata_value(item, depth=depth + 1, seen=seen) for item in value]
        finally:
            seen.remove(value_id)
    raise _raise_validation('Checkpoint store rejected invalid metadata.', code='CHECKPOINT_STORE_INVALID_METADATA')


def normalize_checkpoint_metadata(metadata: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return lossless, JSON-compatible checkpoint metadata."""

    if metadata is None:
        return {}
    if not isinstance(metadata, Mapping):
        raise _raise_validation('Checkpoint store rejected invalid metadata.', code='CHECKPOINT_STORE_INVALID_METADATA')
    return _normalize_metadata_value(metadata, depth=0, seen=set())


def _freeze_metadata(metadata: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return MappingProxyType(normalize_checkpoint_metadata(metadata))


def _canonicalize_metadata_value(value: Any) -> tuple[Any, ...]:
    if value is None:
        return ('null',)
    if isinstance(value, bool):
        return ('bool', value)
    if isinstance(value, int):
        return ('int', value)
    if isinstance(value, float):
        return ('float', value)
    if isinstance(value, str):
        return ('str', value)
    if isinstance(value, list):
        return ('list', tuple(_canonicalize_metadata_value(item) for item in value))
    if isinstance(value, Mapping):
        return (
            'object',
            tuple(
                (key, _canonicalize_metadata_value(value[key]))
                for key in sorted(value.keys())
            ),
        )
    raise _raise_validation('Checkpoint store rejected invalid metadata.', code='CHECKPOINT_STORE_INVALID_METADATA')


def canonicalize_checkpoint_metadata(metadata: Mapping[str, Any] | None) -> tuple[Any, ...]:
    """Return a deterministic comparison form for checkpoint metadata."""

    return _canonicalize_metadata_value(normalize_checkpoint_metadata(metadata))


@dataclass(frozen=True, slots=True)
class CheckpointWriteRequest:
    """Body-aware checkpoint write request."""

    run_id: int | str
    checkpoint_id: str
    body: bytes = field(repr=False)
    serializer_name: str
    serializer_version: int
    content_type: str
    checkpoint_namespace: str = field(default='', repr=False)
    parent_checkpoint_id: str | None = field(default=None, repr=False)
    metadata: Mapping[str, Any] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, 'run_id', normalize_checkpoint_run_id(self.run_id))
        object.__setattr__(self, 'checkpoint_namespace', normalize_checkpoint_namespace(self.checkpoint_namespace))
        object.__setattr__(self, 'checkpoint_id', normalize_checkpoint_id(self.checkpoint_id))
        parent_checkpoint_id = self.parent_checkpoint_id
        if parent_checkpoint_id is not None:
            object.__setattr__(self, 'parent_checkpoint_id', normalize_checkpoint_id(parent_checkpoint_id))
        object.__setattr__(self, 'body', normalize_checkpoint_body(self.body))
        object.__setattr__(self, 'serializer_name', normalize_checkpoint_serializer_name(self.serializer_name))
        object.__setattr__(self, 'serializer_version', normalize_checkpoint_serializer_version(self.serializer_version))
        object.__setattr__(self, 'content_type', normalize_checkpoint_content_type(self.content_type))
        if self.parent_checkpoint_id is not None and self.parent_checkpoint_id == self.checkpoint_id:
            raise _raise_validation('Checkpoint store rejected a self-parent checkpoint request.', code='CHECKPOINT_STORE_SELF_PARENT')
        object.__setattr__(self, 'metadata', _freeze_metadata(self.metadata))


@dataclass(frozen=True, slots=True)
class StoredCheckpoint:
    """Normalized checkpoint descriptor stored by checkpoint stores."""

    run_id: int | str
    checkpoint_namespace: str
    checkpoint_id: str
    parent_checkpoint_id: str | None = field(default=None, repr=False)
    revision: int = 0
    serializer_name: str = ''
    serializer_version: int = 0
    content_type: str = ''
    size: int = 0
    digest: str = ''
    metadata: Mapping[str, Any] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, 'run_id', normalize_checkpoint_run_id(self.run_id))
        object.__setattr__(self, 'checkpoint_namespace', normalize_checkpoint_namespace(self.checkpoint_namespace))
        object.__setattr__(self, 'checkpoint_id', normalize_checkpoint_id(self.checkpoint_id))
        parent_checkpoint_id = self.parent_checkpoint_id
        if parent_checkpoint_id is not None:
            object.__setattr__(self, 'parent_checkpoint_id', normalize_checkpoint_id(parent_checkpoint_id))
        if isinstance(self.revision, bool) or not isinstance(self.revision, int) or self.revision <= 0:
            raise CheckpointIntegrityError(
                'Checkpoint store recorded an invalid checkpoint revision.',
                code='CHECKPOINT_STORE_INVALID_REVISION',
                component=_CHECKPOINT_COMPONENT,
            )
        object.__setattr__(self, 'serializer_name', normalize_checkpoint_serializer_name(self.serializer_name))
        object.__setattr__(self, 'serializer_version', normalize_checkpoint_serializer_version(self.serializer_version))
        object.__setattr__(self, 'content_type', normalize_checkpoint_content_type(self.content_type))
        if isinstance(self.size, bool) or not isinstance(self.size, int) or self.size < 0:
            raise CheckpointIntegrityError(
                'Checkpoint store recorded an invalid checkpoint size.',
                code='CHECKPOINT_STORE_INVALID_SIZE',
                component=_CHECKPOINT_COMPONENT,
            )
        if not isinstance(self.digest, str) or not self.digest.startswith('sha256:') or len(self.digest) != len('sha256:') + 64:
            raise CheckpointIntegrityError(
                'Checkpoint store recorded an invalid checkpoint digest.',
                code='CHECKPOINT_STORE_INVALID_DIGEST',
                component=_CHECKPOINT_COMPONENT,
            )
        object.__setattr__(self, 'metadata', _freeze_metadata(self.metadata))


@dataclass(frozen=True, slots=True)
class CheckpointReadResult:
    """Checkpoint descriptor plus body returned from checkpoint reads."""

    checkpoint: StoredCheckpoint
    body: bytes = field(repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.checkpoint, StoredCheckpoint):
            raise _raise_validation('Checkpoint store rejected an invalid checkpoint read result.', code='CHECKPOINT_STORE_INVALID_READ_RESULT')
        object.__setattr__(self, 'body', normalize_checkpoint_body(self.body))


@runtime_checkable
class CheckpointStore(Protocol):
    def save(self, request: CheckpointWriteRequest) -> StoredCheckpoint: ...
    def load_latest(self, run_id: int | str, *, checkpoint_namespace: str = '') -> CheckpointReadResult | None: ...
    def load_checkpoint(self, run_id: int | str, checkpoint_id: str, *, checkpoint_namespace: str = '') -> CheckpointReadResult | None: ...
    def list_for_run(self, run_id: int | str, *, checkpoint_namespace: str = '') -> list[StoredCheckpoint]: ...
