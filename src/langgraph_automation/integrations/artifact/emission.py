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

from langgraph_automation.api.errors import ArtifactConflictError, ArtifactValidationError
from langgraph_automation.core.redaction import redact_mapping
from langgraph_automation.core.summary import hash_text
from langgraph_automation.integrations.artifact.base import normalize_artifact_run_id
from langgraph_automation.integrations.artifact.keys import validate_storage_key

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
    'normalize_artifact_occurrence',
    'normalize_artifact_slot',
]

_ARTIFACT_EMISSION_COMPONENT = 'artifact_emission'
_MAX_IDENTIFIER_LENGTH = 255
_MAX_METADATA_DEPTH = 16
_MAX_METADATA_ITEMS = 1000
_MAX_METADATA_STRING_LENGTH = 65_536
_ARTIFACT_SLOT_RE = re.compile(r'^[a-z0-9][a-z0-9-]*$')


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


def _normalize_artifact_label(value: str, *, code: str, error_type: type[ArtifactEmissionValidationError]) -> str:
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
    if not value or len(value) > _MAX_IDENTIFIER_LENGTH or '\x00' in value:
        raise error_type(
            'Artifact emission rejected an invalid identifier.',
            code=code,
            component=_ARTIFACT_EMISSION_COMPONENT,
        )
    normalized = value.lower()
    if normalized != value or not _ARTIFACT_SLOT_RE.fullmatch(normalized):
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
    if not normalized or len(normalized) > _MAX_IDENTIFIER_LENGTH or '\x00' in normalized:
        raise _raise_serialization_error(
            'Artifact emission rejected an invalid content type.',
            code='ARTIFACT_EMISSION_INVALID_CONTENT_TYPE',
        )
    parts = [part.strip() for part in normalized.split(';')]
    base = parts[0]
    if not base or '/' not in base or base.count('/') != 1 or any(ch.isspace() for ch in base):
        raise _raise_serialization_error(
            'Artifact emission rejected an invalid content type.',
            code='ARTIFACT_EMISSION_INVALID_CONTENT_TYPE',
        )
    parameters: list[str] = []
    for parameter in parts[1:]:
        if not parameter:
            raise _raise_serialization_error(
                'Artifact emission rejected an invalid content type.',
                code='ARTIFACT_EMISSION_INVALID_CONTENT_TYPE',
            )
        if '\x00' in parameter or any(ch in parameter for ch in '\r\n\t'):
            raise _raise_serialization_error(
                'Artifact emission rejected an invalid content type.',
                code='ARTIFACT_EMISSION_INVALID_CONTENT_TYPE',
            )
        parameters.append(parameter)
    return '; '.join([base, *parameters]) if parameters else base


def _normalize_metadata_value(value: Any, *, depth: int, seen: set[int]) -> Any:
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
        if len(value) > _MAX_METADATA_ITEMS:
            raise ArtifactSerializationContractError(
                'Artifact emission rejected invalid metadata.',
                code='ARTIFACT_EMISSION_INVALID_METADATA',
                component=_ARTIFACT_EMISSION_COMPONENT,
            )
        seen.add(value_id)
        try:
            normalized: dict[str, Any] = {}
            for key in value.keys():
                if not isinstance(key, str):
                    raise ArtifactSerializationContractError(
                        'Artifact emission rejected invalid metadata.',
                        code='ARTIFACT_EMISSION_INVALID_METADATA',
                        component=_ARTIFACT_EMISSION_COMPONENT,
                    )
                if len(key) > _MAX_IDENTIFIER_LENGTH:
                    raise ArtifactSerializationContractError(
                        'Artifact emission rejected invalid metadata.',
                        code='ARTIFACT_EMISSION_INVALID_METADATA',
                        component=_ARTIFACT_EMISSION_COMPONENT,
                    )
                normalized[key] = _normalize_metadata_value(value[key], depth=depth + 1, seen=seen)
            return normalized
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
        if len(value) > _MAX_METADATA_ITEMS:
            raise ArtifactSerializationContractError(
                'Artifact emission rejected invalid metadata.',
                code='ARTIFACT_EMISSION_INVALID_METADATA',
                component=_ARTIFACT_EMISSION_COMPONENT,
            )
        seen.add(value_id)
        try:
            return [_normalize_metadata_value(item, depth=depth + 1, seen=seen) for item in value]
        finally:
            seen.remove(value_id)
    raise ArtifactSerializationContractError(
        'Artifact emission rejected invalid metadata.',
        code='ARTIFACT_EMISSION_INVALID_METADATA',
        component=_ARTIFACT_EMISSION_COMPONENT,
    )


def normalize_artifact_metadata(metadata: Mapping[str, Any] | None) -> Mapping[str, Any]:
    """Return a bounded, JSON-compatible metadata mapping."""

    if metadata is None:
        return MappingProxyType({})
    if not isinstance(metadata, Mapping):
        raise ArtifactSerializationContractError(
            'Artifact emission rejected invalid metadata.',
            code='ARTIFACT_EMISSION_INVALID_METADATA',
            component=_ARTIFACT_EMISSION_COMPONENT,
        )
    redacted = redact_mapping(metadata)
    normalized = _normalize_metadata_value(redacted, depth=0, seen=set())
    if not isinstance(normalized, dict):
        raise ArtifactSerializationContractError(
            'Artifact emission rejected invalid metadata.',
            code='ARTIFACT_EMISSION_INVALID_METADATA',
            component=_ARTIFACT_EMISSION_COMPONENT,
        )
    return MappingProxyType(normalized)


def canonicalize_artifact_metadata(metadata: Mapping[str, Any] | None) -> str:
    """Return a stable comparison token for artifact metadata."""

    normalized = normalize_artifact_metadata(metadata)
    return hash_text(json.dumps(dict(normalized), ensure_ascii=False, sort_keys=True, separators=(',', ':'), default=str))


@dataclass(frozen=True, slots=True)
class ArtifactSlot:
    """Stable logical artifact slot."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, 'value', _normalize_artifact_label(self.value, code='ARTIFACT_EMISSION_INVALID_SLOT', error_type=ArtifactSlotError))


@dataclass(frozen=True, slots=True)
class ArtifactOccurrence:
    """Stable caller-issued artifact occurrence discriminator."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, 'value', _normalize_artifact_label(self.value, code='ARTIFACT_EMISSION_INVALID_OCCURRENCE', error_type=ArtifactOccurrenceError))


@dataclass(frozen=True, slots=True)
class ArtifactEmissionContext:
    """Execution context that injects the run identity into an emission request."""

    run_id: int | str

    def __post_init__(self) -> None:
        object.__setattr__(self, 'run_id', normalize_artifact_run_id(self.run_id))


@dataclass(frozen=True, slots=True)
class ArtifactIdentity:
    """Deterministic logical artifact identity."""

    run_id: int | str
    slot: ArtifactSlot | str
    occurrence: ArtifactOccurrence | str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, 'run_id', normalize_artifact_run_id(self.run_id))
        object.__setattr__(self, 'slot', normalize_artifact_slot(self.slot))
        object.__setattr__(self, 'occurrence', normalize_artifact_occurrence(self.occurrence))


@dataclass(frozen=True, slots=True)
class ArtifactEmissionRequest:
    """Explicit artifact emission request.

    The request is body-aware and store-independent. It carries the logical
    artifact contract only; the execution context supplies ``run_id`` separately.
    """

    slot: ArtifactSlot | str
    body: bytes = field(repr=False)
    occurrence: ArtifactOccurrence | str | None = None
    content_type: str = ''
    metadata: Mapping[str, Any] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, 'slot', normalize_artifact_slot(self.slot))
        object.__setattr__(self, 'occurrence', normalize_artifact_occurrence(self.occurrence))
        object.__setattr__(self, 'body', normalize_artifact_body(self.body))
        object.__setattr__(self, 'content_type', normalize_artifact_content_type(self.content_type))
        object.__setattr__(self, 'metadata', normalize_artifact_metadata(self.metadata))


def build_artifact_identity(
    *,
    run_id: int | str,
    slot: ArtifactSlot | str,
    occurrence: ArtifactOccurrence | str | None = None,
) -> ArtifactIdentity:
    """Return the deterministic logical identity for an explicit artifact."""

    return ArtifactIdentity(run_id=run_id, slot=slot, occurrence=occurrence)


def _encode_identity_component(value: int | str) -> str:
    return quote(str(value), safe='')


def build_artifact_storage_key(identity: ArtifactIdentity) -> str:
    """Return a deterministic opaque storage key for a logical artifact."""

    normalized_identity = build_artifact_identity(
        run_id=identity.run_id,
        slot=identity.slot,
        occurrence=identity.occurrence,
    )
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
    context: ArtifactEmissionContext | int | str,
    request: ArtifactEmissionRequest,
) -> tuple[Any, ...]:
    """Return a deterministic logical equivalence token for an emission request."""

    emission_context = context if isinstance(context, ArtifactEmissionContext) else ArtifactEmissionContext(context)
    identity = build_artifact_identity(run_id=emission_context.run_id, slot=request.slot, occurrence=request.occurrence)
    return (
        identity,
        request.body,
        request.content_type,
        canonicalize_artifact_metadata(request.metadata),
    )


@runtime_checkable
class ArtifactEmitter(Protocol):
    """Future logical emission boundary.

    The emitter is store-independent at X2. X4 can connect an implementation to
    the artifact store protocol.
    """

    def emit(self, context: ArtifactEmissionContext, request: ArtifactEmissionRequest) -> ArtifactIdentity: ...
