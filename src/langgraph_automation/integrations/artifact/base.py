"""Artifact store interfaces and body-aware value types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, runtime_checkable

from langgraph_automation.api.errors import (
    ArtifactConflictError,
    ArtifactIntegrityError,
    ArtifactPersistenceError,
    ArtifactStoreError,
    ArtifactValidationError,
)
from langgraph_automation.core.redaction import redact_mapping
from langgraph_automation.core.summary import hash_text

from .keys import validate_storage_key

__all__ = [
    'ArtifactStore',
    'ArtifactWriteRequest',
    'StoredArtifact',
    'ArtifactReadResult',
    'ArtifactStoreError',
    'ArtifactValidationError',
    'ArtifactConflictError',
    'ArtifactIntegrityError',
    'ArtifactPersistenceError',
    'normalize_artifact_body',
    'normalize_artifact_content_type',
    'normalize_artifact_metadata',
    'normalize_artifact_name',
    'normalize_artifact_kind',
    'normalize_artifact_run_id',
]

_ARTIFACT_COMPONENT = 'artifact_store'


def normalize_artifact_run_id(run_id: int | str) -> int | str:
    """Return a normalized run identifier."""

    if isinstance(run_id, bool) or not isinstance(run_id, (int, str)):
        raise ArtifactValidationError(
            'Artifact store rejected an invalid run identifier.',
            code='ARTIFACT_STORE_INVALID_RUN_ID',
            component=_ARTIFACT_COMPONENT,
        )
    if isinstance(run_id, str):
        normalized = run_id.strip()
        if not normalized:
            raise ArtifactValidationError(
                'Artifact store rejected an invalid run identifier.',
                code='ARTIFACT_STORE_INVALID_RUN_ID',
                component=_ARTIFACT_COMPONENT,
            )
        return normalized
    return run_id


def normalize_artifact_storage_key(storage_key: str) -> str:
    """Return a validated opaque storage key."""

    if not isinstance(storage_key, str):
        raise ArtifactValidationError(
            'Artifact store rejected an invalid storage key.',
            code='ARTIFACT_STORE_INVALID_STORAGE_KEY',
            component=_ARTIFACT_COMPONENT,
        )
    return validate_storage_key(storage_key)


def normalize_artifact_name(name: str) -> str:
    """Return a normalized artifact name."""

    if not isinstance(name, str):
        raise ArtifactValidationError(
            'Artifact store rejected an invalid artifact name.',
            code='ARTIFACT_STORE_INVALID_NAME',
            component=_ARTIFACT_COMPONENT,
        )
    normalized = name.strip()
    if not normalized:
        raise ArtifactValidationError(
            'Artifact store rejected an invalid artifact name.',
            code='ARTIFACT_STORE_INVALID_NAME',
            component=_ARTIFACT_COMPONENT,
        )
    return normalized


def normalize_artifact_kind(kind: str) -> str:
    """Return a normalized artifact kind."""

    if not isinstance(kind, str):
        raise ArtifactValidationError(
            'Artifact store rejected an invalid artifact kind.',
            code='ARTIFACT_STORE_INVALID_KIND',
            component=_ARTIFACT_COMPONENT,
        )
    normalized = kind.strip()
    if not normalized:
        raise ArtifactValidationError(
            'Artifact store rejected an invalid artifact kind.',
            code='ARTIFACT_STORE_INVALID_KIND',
            component=_ARTIFACT_COMPONENT,
        )
    return normalized


def normalize_artifact_content_type(content_type: str | None) -> str | None:
    """Return a normalized content type or None."""

    if content_type is None:
        return None
    if not isinstance(content_type, str):
        raise ArtifactValidationError(
            'Artifact store rejected an invalid content type.',
            code='ARTIFACT_STORE_INVALID_CONTENT_TYPE',
            component=_ARTIFACT_COMPONENT,
        )
    normalized = content_type.strip().lower()
    if not normalized:
        raise ArtifactValidationError(
            'Artifact store rejected an invalid content type.',
            code='ARTIFACT_STORE_INVALID_CONTENT_TYPE',
            component=_ARTIFACT_COMPONENT,
        )
    if any(ch in normalized for ch in '\r\n'):
        raise ArtifactValidationError(
            'Artifact store rejected an invalid content type.',
            code='ARTIFACT_STORE_INVALID_CONTENT_TYPE',
            component=_ARTIFACT_COMPONENT,
        )
    return normalized


def _normalize_json_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        if isinstance(value, str):
            return value
        return value
    if isinstance(value, Mapping):
        return {str(key): _normalize_json_value(nested) for key, nested in value.items()}
    if isinstance(value, tuple):
        return [_normalize_json_value(item) for item in value]
    if isinstance(value, list):
        return [_normalize_json_value(item) for item in value]
    raise ArtifactValidationError(
        'Artifact store rejected invalid metadata.',
        code='ARTIFACT_STORE_INVALID_METADATA',
        component=_ARTIFACT_COMPONENT,
    )


def normalize_artifact_metadata(metadata: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return redacted, JSON-compatible artifact metadata."""

    if metadata is None:
        return {}
    if not isinstance(metadata, Mapping):
        raise ArtifactValidationError(
            'Artifact store rejected invalid metadata.',
            code='ARTIFACT_STORE_INVALID_METADATA',
            component=_ARTIFACT_COMPONENT,
        )
    redacted = redact_mapping(metadata)
    normalized = _normalize_json_value(redacted)
    if not isinstance(normalized, dict):
        raise ArtifactValidationError(
            'Artifact store rejected invalid metadata.',
            code='ARTIFACT_STORE_INVALID_METADATA',
            component=_ARTIFACT_COMPONENT,
        )
    return normalized


def normalize_artifact_body(body: Any) -> bytes:
    """Return a validated artifact body."""

    if not isinstance(body, (bytes, bytearray, memoryview)):
        raise ArtifactValidationError(
            'Artifact store rejected an invalid body payload.',
            code='ARTIFACT_STORE_INVALID_BODY',
            component=_ARTIFACT_COMPONENT,
        )
    return bytes(body)


def _artifact_metadata_identity(metadata: Mapping[str, Any]) -> str:
    return hash_text(repr(sorted(metadata.items())))


@dataclass(frozen=True, slots=True)
class ArtifactWriteRequest:
    """Body-aware artifact write request."""

    run_id: int | str
    storage_key: str
    body: bytes = field(repr=False)
    name: str = ''
    kind: str = ''
    content_type: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, 'run_id', normalize_artifact_run_id(self.run_id))
        object.__setattr__(self, 'storage_key', str(self.storage_key))
        object.__setattr__(self, 'body', normalize_artifact_body(self.body))
        object.__setattr__(self, 'name', normalize_artifact_name(self.name) if self.name else '')
        object.__setattr__(self, 'kind', normalize_artifact_kind(self.kind) if self.kind else '')
        object.__setattr__(self, 'content_type', normalize_artifact_content_type(self.content_type))
        object.__setattr__(self, 'metadata', normalize_artifact_metadata(self.metadata))


@dataclass(frozen=True, slots=True)
class StoredArtifact:
    """Normalized artifact descriptor stored by artifact stores."""

    run_id: int | str
    storage_key: str
    name: str = ''
    kind: str = ''
    content_type: str | None = None
    size: int = 0
    digest: str = ''
    metadata: dict[str, Any] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, 'run_id', normalize_artifact_run_id(self.run_id))
        try:
            object.__setattr__(self, 'storage_key', normalize_artifact_storage_key(self.storage_key))
        except ValueError as exc:
            raise ArtifactValidationError(
                'Artifact store rejected an invalid storage key.',
                code='ARTIFACT_STORE_INVALID_STORAGE_KEY',
                component=_ARTIFACT_COMPONENT,
            ) from exc
        object.__setattr__(self, 'name', normalize_artifact_name(self.name) if self.name else '')
        object.__setattr__(self, 'kind', normalize_artifact_kind(self.kind) if self.kind else '')
        object.__setattr__(self, 'content_type', normalize_artifact_content_type(self.content_type))
        if isinstance(self.size, bool) or not isinstance(self.size, int) or self.size < 0:
            raise ArtifactIntegrityError(
                'Artifact store recorded an invalid artifact size.',
                code='ARTIFACT_STORE_INVALID_SIZE',
                component=_ARTIFACT_COMPONENT,
            )
        if not isinstance(self.digest, str) or not self.digest.startswith('sha256:'):
            raise ArtifactIntegrityError(
                'Artifact store recorded an invalid artifact digest.',
                code='ARTIFACT_STORE_INVALID_DIGEST',
                component=_ARTIFACT_COMPONENT,
            )
        object.__setattr__(self, 'metadata', normalize_artifact_metadata(self.metadata))

    def canonical_metadata_identity(self) -> str:
        return _artifact_metadata_identity(self.metadata)


@dataclass(frozen=True, slots=True)
class ArtifactReadResult:
    """Artifact descriptor plus body payload."""

    artifact: StoredArtifact
    body: bytes = field(repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.artifact, StoredArtifact):
            raise ArtifactIntegrityError(
                'Artifact store returned an invalid artifact descriptor.',
                code='ARTIFACT_STORE_INVALID_DESCRIPTOR',
                component=_ARTIFACT_COMPONENT,
            )
        object.__setattr__(self, 'body', normalize_artifact_body(self.body))


@runtime_checkable
class ArtifactStore(Protocol):
    def put(self, request: ArtifactWriteRequest) -> StoredArtifact: ...
    def get(self, storage_key: str) -> ArtifactReadResult | None: ...
    def list_for_run(self, run_id: int | str) -> list[StoredArtifact]: ...
