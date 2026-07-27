"""Explicit artifact emission contract.

This module defines the logical artifact contract above the storage layer.
It does not construct concrete stores, does not import runtime assembly, and
does not perform persistence writes.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from math import isfinite
from types import MappingProxyType
from typing import Any, Mapping, Protocol, runtime_checkable
from urllib.parse import quote

from cobalt_wren.api.errors import ArtifactConflictError, ArtifactValidationError
from cobalt_wren.core.redaction import redact_mapping
from cobalt_wren.core.summary import hash_text
from cobalt_wren.integrations.artifact.keys import validate_storage_key

__all__ = [
    'ArtifactEmissionContext',
    'ArtifactEmissionConflict',
    'ArtifactEmissionError',
    'ArtifactEmissionRequest',
    'ArtifactEmissionValidationError',
    'ArtifactEmitter',
    'ArtifactIdentity',
    'ArtifactOccurrence',
    'ArtifactOccurrenceError',
    'ArtifactSerializationContractError',
    'ArtifactSlot',
    'ArtifactSlotError',
    'build_artifact_identity',
    'build_artifact_storage_key',
    'artifact_emission_request_signature',
    'artifact_emission_requests_equivalent',
    'validate_duplicate_emission',
    'normalize_artifact_occurrence',
    'normalize_artifact_slot',
]

_ARTIFACT_EMISSION_COMPONENT = 'artifact_emission'
_MAX_RUN_ID = 2**63 - 1
_MAX_SLOT_LENGTH = 64
_MAX_OCCURRENCE_LENGTH = 64
_MAX_CONTENT_TYPE_LENGTH = 255
_MAX_METADATA_DEPTH = 8
_MAX_METADATA_TOP_LEVEL_KEYS = 64
_MAX_METADATA_MAPPING_ITEMS = 64
_MAX_METADATA_LIST_ITEMS = 256
_MAX_METADATA_STRING_LENGTH = 4096
_MAX_METADATA_TOTAL_NODES = 2048
_MAX_METADATA_KEY_LENGTH = 128
_LOGICAL_IDENTIFIER_RE = re.compile(r'^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$')
_MEDIA_TYPE_RE = re.compile(r'^[a-z0-9!#$&^_.+-]+/[a-z0-9!#$&^_.+-]+$')
_MEDIA_TYPE_PARAMETER_RE = re.compile(r'^[a-z0-9!#$&^_.+-]+=[a-z0-9!#$&^_.+-]+$')


class ArtifactEmissionError(ArtifactValidationError):
    def __init__(
        self,
        safe_message: str,
        *,
        code: str,
        component: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(
            safe_message,
            code=code,
            component=component or _ARTIFACT_EMISSION_COMPONENT,
            metadata=metadata,
        )


class ArtifactEmissionValidationError(ArtifactEmissionError):
    pass


class ArtifactSlotError(ArtifactEmissionValidationError):
    pass


class ArtifactOccurrenceError(ArtifactEmissionValidationError):
    pass


class ArtifactSerializationContractError(ArtifactEmissionValidationError):
    pass


class ArtifactEmissionConflict(ArtifactConflictError):
    def __init__(
        self,
        safe_message: str,
        *,
        code: str,
        component: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(
            safe_message,
            code=code,
            component=component or _ARTIFACT_EMISSION_COMPONENT,
            metadata=metadata,
        )


def _raise_serialization_error(message: str, *, code: str) -> ArtifactSerializationContractError:
    return ArtifactSerializationContractError(message, code=code, component=_ARTIFACT_EMISSION_COMPONENT)


def _normalize_artifact_run_id(run_id: int) -> int:
    if isinstance(run_id, bool) or not isinstance(run_id, int):
        raise ArtifactEmissionValidationError(
            'Artifact emission rejected an invalid run identifier.',
            code='ARTIFACT_EMISSION_INVALID_RUN_ID',
            component=_ARTIFACT_EMISSION_COMPONENT,
        )
    if run_id <= 0 or run_id > _MAX_RUN_ID:
        raise ArtifactEmissionValidationError(
            'Artifact emission rejected an invalid run identifier.',
            code='ARTIFACT_EMISSION_INVALID_RUN_ID',
            component=_ARTIFACT_EMISSION_COMPONENT,
        )
    return run_id


def _normalize_artifact_label(
    value: str,
    *,
    code: str,
    error_type: type[ArtifactEmissionValidationError],
    max_length: int,
) -> str:
    if not isinstance(value, str):
        raise error_type(
            'Artifact emission rejected an invalid identifier.',
            code=code,
            component=_ARTIFACT_EMISSION_COMPONENT,
        )
    if value != value.strip():
        raise error_type(
            'Artifact emission rejected an invalid identifier.',
            code=code,
            component=_ARTIFACT_EMISSION_COMPONENT,
        )
    if not value or len(value) > max_length or '\x00' in value:
        raise error_type(
            'Artifact emission rejected an invalid identifier.',
            code=code,
            component=_ARTIFACT_EMISSION_COMPONENT,
        )
    normalized = value.lower()
    if normalized != value or not _LOGICAL_IDENTIFIER_RE.fullmatch(normalized):
        raise error_type(
            'Artifact emission rejected an invalid identifier.',
            code=code,
            component=_ARTIFACT_EMISSION_COMPONENT,
        )
    return normalized


def normalize_artifact_slot(slot: ArtifactSlot | str) -> ArtifactSlot:
    """Return a normalized artifact slot."""

    if isinstance(slot, ArtifactSlot):
        return slot
    return ArtifactSlot(slot)


def normalize_artifact_occurrence(occurrence: ArtifactOccurrence | str | None) -> ArtifactOccurrence | None:
    """Return a normalized artifact occurrence or None."""

    if occurrence is None:
        return None
    if isinstance(occurrence, ArtifactOccurrence):
        return occurrence
    return ArtifactOccurrence(occurrence)


def normalize_artifact_body(body: Any) -> bytes:
    """Return validated artifact body bytes."""

    if not isinstance(body, (bytes, bytearray, memoryview)):
        raise _raise_serialization_error(
            'Artifact emission rejected an invalid body payload.',
            code='ARTIFACT_EMISSION_INVALID_BODY',
        )
    return bytes(body)


def normalize_artifact_content_type(content_type: str) -> str:
    """Return a normalized content type."""

    if not isinstance(content_type, str):
        raise _raise_serialization_error(
            'Artifact emission rejected an invalid content type.',
            code='ARTIFACT_EMISSION_INVALID_CONTENT_TYPE',
        )
    normalized = content_type.strip().lower()
    if not normalized or len(normalized) > _MAX_CONTENT_TYPE_LENGTH or '\x00' in normalized:
        raise _raise_serialization_error(
            'Artifact emission rejected an invalid content type.',
            code='ARTIFACT_EMISSION_INVALID_CONTENT_TYPE',
        )
    parts = [part.strip() for part in normalized.split(';')]
    base = parts[0]
    if not base or not _MEDIA_TYPE_RE.fullmatch(base):
        raise _raise_serialization_error(
            'Artifact emission rejected an invalid content type.',
            code='ARTIFACT_EMISSION_INVALID_CONTENT_TYPE',
        )
    parameters: list[str] = []
    for parameter in parts[1:]:
        if not parameter or any(ch.isspace() for ch in parameter):
            raise _raise_serialization_error(
                'Artifact emission rejected an invalid content type.',
                code='ARTIFACT_EMISSION_INVALID_CONTENT_TYPE',
            )
        if '\x00' in parameter or not _MEDIA_TYPE_PARAMETER_RE.fullmatch(parameter):
            raise _raise_serialization_error(
                'Artifact emission rejected an invalid content type.',
                code='ARTIFACT_EMISSION_INVALID_CONTENT_TYPE',
            )
        parameters.append(parameter)
    return '; '.join([base, *parameters]) if parameters else base


def _freeze_metadata_value(
    value: Any,
    *,
    depth: int,
    seen: set[int],
    counts: dict[str, int],
) -> Any:
    counts['nodes'] += 1
    if counts['nodes'] > _MAX_METADATA_TOTAL_NODES:
        raise ArtifactSerializationContractError(
            'Artifact emission rejected invalid metadata.',
            code='ARTIFACT_EMISSION_INVALID_METADATA',
            component=_ARTIFACT_EMISSION_COMPONENT,
        )
    if depth > _MAX_METADATA_DEPTH:
        raise ArtifactSerializationContractError(
            'Artifact emission rejected invalid metadata.',
            code='ARTIFACT_EMISSION_INVALID_METADATA',
            component=_ARTIFACT_EMISSION_COMPONENT,
        )
    if value is None or isinstance(value, bool) or isinstance(value, int):
        return value
    if isinstance(value, float):
        if not isfinite(value):
            raise ArtifactSerializationContractError(
                'Artifact emission rejected invalid metadata.',
                code='ARTIFACT_EMISSION_INVALID_METADATA',
                component=_ARTIFACT_EMISSION_COMPONENT,
            )
        return value
    if isinstance(value, str):
        if len(value) > _MAX_METADATA_STRING_LENGTH:
            raise ArtifactSerializationContractError(
                'Artifact emission rejected invalid metadata.',
                code='ARTIFACT_EMISSION_INVALID_METADATA',
                component=_ARTIFACT_EMISSION_COMPONENT,
            )
        return value
    if isinstance(value, (bytes, bytearray, memoryview)):
        raise ArtifactSerializationContractError(
            'Artifact emission rejected invalid metadata.',
            code='ARTIFACT_EMISSION_INVALID_METADATA',
            component=_ARTIFACT_EMISSION_COMPONENT,
        )
    if isinstance(value, Mapping):
        value_id = id(value)
        if value_id in seen:
            raise ArtifactSerializationContractError(
                'Artifact emission rejected invalid metadata.',
                code='ARTIFACT_EMISSION_INVALID_METADATA',
                component=_ARTIFACT_EMISSION_COMPONENT,
            )
        if depth == 0 and len(value) > _MAX_METADATA_TOP_LEVEL_KEYS:
            raise ArtifactSerializationContractError(
                'Artifact emission rejected invalid metadata.',
                code='ARTIFACT_EMISSION_INVALID_METADATA',
                component=_ARTIFACT_EMISSION_COMPONENT,
            )
        if len(value) > _MAX_METADATA_MAPPING_ITEMS:
            raise ArtifactSerializationContractError(
                'Artifact emission rejected invalid metadata.',
                code='ARTIFACT_EMISSION_INVALID_METADATA',
                component=_ARTIFACT_EMISSION_COMPONENT,
            )
        seen.add(value_id)
        try:
            normalized: dict[str, Any] = {}
            for key in value.keys():
                if not isinstance(key, str) or not key or len(key) > _MAX_METADATA_KEY_LENGTH:
                    raise ArtifactSerializationContractError(
                        'Artifact emission rejected invalid metadata.',
                        code='ARTIFACT_EMISSION_INVALID_METADATA',
                        component=_ARTIFACT_EMISSION_COMPONENT,
                    )
                normalized[key] = _freeze_metadata_value(value[key], depth=depth + 1, seen=seen, counts=counts)
            return MappingProxyType(normalized)
        finally:
            seen.remove(value_id)
    if isinstance(value, list):
        value_id = id(value)
        if value_id in seen:
            raise ArtifactSerializationContractError(
                'Artifact emission rejected invalid metadata.',
                code='ARTIFACT_EMISSION_INVALID_METADATA',
                component=_ARTIFACT_EMISSION_COMPONENT,
            )
        if len(value) > _MAX_METADATA_LIST_ITEMS:
            raise ArtifactSerializationContractError(
                'Artifact emission rejected invalid metadata.',
                code='ARTIFACT_EMISSION_INVALID_METADATA',
                component=_ARTIFACT_EMISSION_COMPONENT,
            )
        seen.add(value_id)
        try:
            return tuple(
                _freeze_metadata_value(item, depth=depth + 1, seen=seen, counts=counts)
                for item in value
            )
        finally:
            seen.remove(value_id)
    raise ArtifactSerializationContractError(
        'Artifact emission rejected invalid metadata.',
        code='ARTIFACT_EMISSION_INVALID_METADATA',
        component=_ARTIFACT_EMISSION_COMPONENT,
    )


def normalize_artifact_metadata(metadata: Mapping[str, Any] | None) -> Mapping[str, Any]:
    """Return a bounded, deeply immutable JSON-compatible metadata mapping."""

    if metadata is None:
        return MappingProxyType({})
    if not isinstance(metadata, Mapping):
        raise ArtifactSerializationContractError(
            'Artifact emission rejected invalid metadata.',
            code='ARTIFACT_EMISSION_INVALID_METADATA',
            component=_ARTIFACT_EMISSION_COMPONENT,
        )
    redacted = redact_mapping(metadata, max_depth=_MAX_METADATA_DEPTH + 2)
    normalized = _freeze_metadata_value(redacted, depth=0, seen=set(), counts={'nodes': 0})
    if not isinstance(normalized, Mapping):
        raise ArtifactSerializationContractError(
            'Artifact emission rejected invalid metadata.',
            code='ARTIFACT_EMISSION_INVALID_METADATA',
            component=_ARTIFACT_EMISSION_COMPONENT,
        )
    return normalized


def canonicalize_artifact_metadata(metadata: Mapping[str, Any] | None) -> str:
    """Return a stable comparison token for artifact metadata."""

    def _thaw(value: Any) -> Any:
        if isinstance(value, Mapping):
            return {str(key): _thaw(nested) for key, nested in value.items()}
        if isinstance(value, tuple):
            return [_thaw(item) for item in value]
        return value

    normalized = normalize_artifact_metadata(metadata)
    return hash_text(json.dumps(_thaw(normalized), ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False))


@dataclass(frozen=True, slots=True)
class ArtifactSlot:
    """Stable logical artifact slot."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            'value',
            _normalize_artifact_label(
                self.value,
                code='ARTIFACT_EMISSION_INVALID_SLOT',
                error_type=ArtifactSlotError,
                max_length=_MAX_SLOT_LENGTH,
            ),
        )


@dataclass(frozen=True, slots=True)
class ArtifactOccurrence:
    """Stable caller-issued artifact occurrence discriminator."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            'value',
            _normalize_artifact_label(
                self.value,
                code='ARTIFACT_EMISSION_INVALID_OCCURRENCE',
                error_type=ArtifactOccurrenceError,
                max_length=_MAX_OCCURRENCE_LENGTH,
            ),
        )


@dataclass(frozen=True, slots=True)
class ArtifactEmissionContext:
    """Execution context that injects the run identity into an emission request."""

    run_id: int

    def __post_init__(self) -> None:
        object.__setattr__(self, 'run_id', _normalize_artifact_run_id(self.run_id))


@dataclass(frozen=True, slots=True)
class ArtifactIdentity:
    """Deterministic logical artifact identity."""

    run_id: int
    slot: ArtifactSlot
    occurrence: ArtifactOccurrence | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, 'run_id', _normalize_artifact_run_id(self.run_id))
        object.__setattr__(self, 'slot', normalize_artifact_slot(self.slot))
        object.__setattr__(self, 'occurrence', normalize_artifact_occurrence(self.occurrence))


@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactEmissionRequest:
    """Explicit artifact emission request.

    The request is body-aware and store-independent. It carries the logical
    artifact contract only; the execution context supplies ``run_id`` separately.
    """

    slot: ArtifactSlot | str
    occurrence: ArtifactOccurrence | str | None = None
    body: bytes = field(repr=False)
    content_type: str
    metadata: Mapping[str, Any] = field(repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, 'slot', normalize_artifact_slot(self.slot))
        object.__setattr__(self, 'occurrence', normalize_artifact_occurrence(self.occurrence))
        object.__setattr__(self, 'body', normalize_artifact_body(self.body))
        object.__setattr__(self, 'content_type', normalize_artifact_content_type(self.content_type))
        object.__setattr__(self, 'metadata', normalize_artifact_metadata(self.metadata))


def build_artifact_identity(
    *,
    context: ArtifactEmissionContext,
    request: ArtifactEmissionRequest,
) -> ArtifactIdentity:
    """Return the deterministic logical identity for an explicit artifact."""

    return ArtifactIdentity(
        run_id=context.run_id,
        slot=normalize_artifact_slot(request.slot),
        occurrence=normalize_artifact_occurrence(request.occurrence),
    )


def _encode_identity_component(value: int | str) -> str:
    return quote(str(value), safe='')


def build_artifact_storage_key(identity: ArtifactIdentity) -> str:
    """Return a deterministic opaque storage key for a logical artifact."""

    normalized_identity = ArtifactIdentity(run_id=identity.run_id, slot=identity.slot, occurrence=identity.occurrence)
    parts = [
        'artifact',
        'v1',
        _encode_identity_component(normalized_identity.run_id),
        _encode_identity_component(normalized_identity.slot.value),
    ]
    if normalized_identity.occurrence is not None:
        parts.append(_encode_identity_component(normalized_identity.occurrence.value))
    storage_key = '/'.join(parts)
    return validate_storage_key(storage_key)


def artifact_emission_request_signature(
    context: ArtifactEmissionContext,
    request: ArtifactEmissionRequest,
) -> tuple[Any, ...]:
    """Return a deterministic logical equivalence token for an emission request."""

    identity = build_artifact_identity(context=context, request=request)
    return (
        identity,
        request.body,
        request.content_type,
        canonicalize_artifact_metadata(request.metadata),
    )


def artifact_emission_requests_equivalent(
    left: ArtifactEmissionRequest,
    right: ArtifactEmissionRequest,
) -> bool:
    """Return True when two explicit emission requests are logically equivalent."""

    return (
        left.slot == right.slot
        and left.occurrence == right.occurrence
        and left.body == right.body
        and left.content_type == right.content_type
        and canonicalize_artifact_metadata(left.metadata) == canonicalize_artifact_metadata(right.metadata)
    )


def validate_duplicate_emission(
    *,
    identity: ArtifactIdentity,
    existing: ArtifactEmissionRequest,
    incoming: ArtifactEmissionRequest,
) -> None:
    """Raise when two requests for the same logical artifact conflict."""

    if artifact_emission_requests_equivalent(existing, incoming):
        return
    raise ArtifactEmissionConflict(
        'Artifact emission rejected a conflicting logical request.',
        code='ARTIFACT_EMISSION_CONFLICT',
        metadata={'slot': identity.slot.value, 'run_id': identity.run_id},
    )


@runtime_checkable
class ArtifactEmitter(Protocol):
    """Future logical emission boundary.

    The emitter is store-independent at X2. X4 can connect an implementation to
    the artifact store protocol.
    """

    def emit(self, context: ArtifactEmissionContext, request: ArtifactEmissionRequest) -> ArtifactIdentity: ...
