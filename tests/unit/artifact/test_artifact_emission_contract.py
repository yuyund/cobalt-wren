"""Contract tests for explicit artifact emission identity."""

from __future__ import annotations

import inspect
from pathlib import Path
from types import MappingProxyType

import pytest

from cobalt_wren.integrations.artifact import emission as emission_module
from cobalt_wren.integrations.artifact.base import ArtifactWriteRequest
from cobalt_wren.integrations.artifact.emission import (
    ArtifactEmissionConflict,
    ArtifactEmissionContext,
    ArtifactEmissionRequest,
    ArtifactIdentity,
    ArtifactOccurrence,
    ArtifactOccurrenceError,
    ArtifactSerializationContractError,
    ArtifactSlot,
    ArtifactSlotError,
    artifact_emission_request_signature,
    artifact_emission_requests_equivalent,
    build_artifact_identity,
    build_artifact_storage_key,
    normalize_artifact_occurrence,
    normalize_artifact_slot,
    validate_duplicate_emission,
)
from cobalt_wren.integrations.artifact.mapping import build_artifact_write_request
from cobalt_wren.integrations.artifact.keys import is_safe_storage_key


def test_artifact_emission_request_fields_are_explicit_and_body_aware() -> None:
    assert tuple(ArtifactEmissionRequest.__dataclass_fields__) == ('slot', 'occurrence', 'body', 'content_type', 'metadata')
    assert tuple(ArtifactIdentity.__dataclass_fields__) == ('run_id', 'slot', 'occurrence')
    assert tuple(ArtifactSlot.__dataclass_fields__) == ('value',)
    assert tuple(ArtifactOccurrence.__dataclass_fields__) == ('value',)
    assert tuple(ArtifactEmissionContext.__dataclass_fields__) == ('run_id',)
    assert ArtifactEmissionRequest.__dataclass_fields__['body'].repr is False
    assert ArtifactEmissionRequest.__dataclass_fields__['metadata'].repr is False
    assert 'run_id' not in inspect.signature(ArtifactEmissionRequest).parameters
    assert 'attempt_id' not in inspect.signature(ArtifactEmissionRequest).parameters
    assert 'required' not in inspect.signature(ArtifactEmissionRequest).parameters
    assert 'best_effort' not in inspect.signature(ArtifactEmissionRequest).parameters


@pytest.mark.parametrize(
    ('slot', 'occurrence'),
    [
        ('a', None),
        ('final-report', '0001'),
        ('generated-image', 'revenue-chart'),
        ('x' * 64, 'y' * 64),
    ],
)
def test_artifact_emission_identity_validation_accepts_canonical_values(
    slot: str | ArtifactSlot,
    occurrence: str | ArtifactOccurrence | None,
) -> None:
    context = ArtifactEmissionContext(run_id=123)
    request = ArtifactEmissionRequest(
        slot=slot,
        occurrence=occurrence,
        body=b'body',
        content_type='application/json',
        metadata={'kind': 'report'},
    )

    identity = build_artifact_identity(context=context, request=request)

    assert identity == ArtifactIdentity(run_id=123, slot=normalize_artifact_slot(slot), occurrence=normalize_artifact_occurrence(occurrence))
    assert artifact_emission_request_signature(context, request)[0] == identity


@pytest.mark.parametrize('bad_slot', ['', ' ', 'Final-Report', '-start', 'end-', 'report/', '/report', 'report/slot', 'report\\slot', 'report..', 'a' * 65])
def test_artifact_slot_validation_rejects_non_canonical_values(bad_slot: str) -> None:
    with pytest.raises(ArtifactSlotError):
        ArtifactSlot(bad_slot)


@pytest.mark.parametrize('bad_occurrence', ['', ' ', 'Run #1', '-start', 'end-', '../occurrence', '/occurrence', 'occurrence/slot', 'occurrence\\slot', 'occurrence..', 'a' * 65])
def test_artifact_occurrence_validation_rejects_non_canonical_values(bad_occurrence: str) -> None:
    with pytest.raises(ArtifactOccurrenceError):
        ArtifactOccurrence(bad_occurrence)


def test_artifact_emission_request_defensively_copies_and_normalizes_input() -> None:
    metadata = {
        'token': 'Authorization: Bearer secret-token /tmp/secret.txt',
        'nested': {'path': '/tmp/secret.txt', 'items': [1, 2, 3]},
    }
    body = bytearray(b'hello world')
    request = ArtifactEmissionRequest(
        slot='final-report',
        occurrence=None,
        body=body,
        content_type='Text/Plain; charset=UTF-8',
        metadata=metadata,
    )

    body[:] = b'changed body'
    metadata['nested']['path'] = 'changed'
    metadata['nested']['items'].append(4)
    metadata['token'] = 'changed'

    assert request.body == b'hello world'
    assert type(request.body) is bytes
    assert request.content_type == 'text/plain; charset=utf-8'
    assert request.metadata['token'] == '***REDACTED***'
    assert isinstance(request.metadata, MappingProxyType)
    assert isinstance(request.metadata['nested'], MappingProxyType)
    assert isinstance(request.metadata['nested']['items'], tuple)
    assert request.metadata['nested']['path'] == '***REDACTED***'
    assert request.metadata['nested']['items'] == (1, 2, 3)
    assert request.metadata['nested']['items'][1] == 2


@pytest.mark.parametrize(
    ('body', 'expected'),
    [
        (b'plain bytes', b'plain bytes'),
        (bytearray(b'buffer'), b'buffer'),
        (memoryview(b'view'), b'view'),
        (b'', b''),
    ],
)
def test_artifact_emission_request_accepts_bytes_like_and_copies_body(body: bytes | bytearray | memoryview, expected: bytes) -> None:
    request = ArtifactEmissionRequest(
        slot='final-report',
        occurrence=None,
        body=body,
        content_type='application/json',
        metadata={},
    )

    assert request.body == expected
    assert type(request.body) is bytes


@pytest.mark.parametrize('body', ['text', 1, object(), None])
def test_artifact_emission_request_rejects_invalid_body_types(body: object) -> None:
    with pytest.raises(ArtifactSerializationContractError):
        ArtifactEmissionRequest(
            slot='final-report',
            occurrence=None,
            body=body,  # type: ignore[arg-type]
            content_type='application/json',
            metadata={},
        )


@pytest.mark.parametrize(
    'content_type',
    [
        'application/pdf',
        'application/json',
        'text/plain; charset=utf-8',
        'image/png',
    ],
)
def test_artifact_emission_request_accepts_valid_content_types(content_type: str) -> None:
    request = ArtifactEmissionRequest(
        slot='final-report',
        occurrence=None,
        body=b'body',
        content_type=content_type,
        metadata={},
    )

    assert request.content_type == content_type.lower()


@pytest.mark.parametrize(
    'content_type',
    [
        '',
        ' ',
        'application/',
        'text/plain; charset=utf 8',
        'text/plain\ncharset=utf-8',
        'a' * 256,
    ],
)
def test_artifact_emission_request_rejects_invalid_content_types(content_type: str) -> None:
    with pytest.raises(ArtifactSerializationContractError):
        ArtifactEmissionRequest(
            slot='final-report',
            occurrence=None,
            body=b'body',
            content_type=content_type,
            metadata={},
        )


def test_artifact_emission_metadata_is_deeply_immutable_and_bounded() -> None:
    metadata = {
        'kind': 'report',
        'nested': {'items': [1, {'page': 1}], 'label': 'summary'},
    }
    request = ArtifactEmissionRequest(
        slot='final-report',
        occurrence=None,
        body=b'body',
        content_type='application/json',
        metadata=metadata,
    )

    metadata['nested']['items'][1]['page'] = 2
    metadata['nested']['items'].append(3)
    metadata['nested']['label'] = 'changed'

    assert request.metadata['nested']['items'] == (1, MappingProxyType({'page': 1}))
    assert request.metadata['nested']['label'] == 'summary'
    with pytest.raises(TypeError):
        request.metadata['nested']['items'][1]['page'] = 2  # type: ignore[index]


def test_artifact_emission_metadata_accepts_boundary_values() -> None:
    accepted_cases = [
        {'top': {f'k{i}': i for i in range(emission_module._MAX_METADATA_TOP_LEVEL_KEYS)}},
        {'nested': {f'k{i}': i for i in range(emission_module._MAX_METADATA_MAPPING_ITEMS)}},
        {'nested': list(range(emission_module._MAX_METADATA_LIST_ITEMS))},
        {'nested': {'label': 'x' * emission_module._MAX_METADATA_STRING_LENGTH}},
        {'nested': {'x' * emission_module._MAX_METADATA_KEY_LENGTH: 1}},
        {'nested': {'a': {'b': {'c': {'d': {'e': {'f': {'g': 1}}}}}}}},
        {'nested': {f'k{i}': [i for i in range(92)] for i in range(22)}},
    ]

    for metadata in accepted_cases:
        request = ArtifactEmissionRequest(
            slot='final-report',
            occurrence=None,
            body=b'body',
            content_type='application/json',
            metadata=metadata,
        )
        assert request.metadata


@pytest.mark.parametrize(
    'metadata',
    [
        {f'k{i}': i for i in range(emission_module._MAX_METADATA_TOP_LEVEL_KEYS + 1)},
        {'nested': {f'k{i}': i for i in range(emission_module._MAX_METADATA_MAPPING_ITEMS + 1)}},
        {'nested': list(range(emission_module._MAX_METADATA_LIST_ITEMS + 1))},
        {'nested': {'label': 'x' * (emission_module._MAX_METADATA_STRING_LENGTH + 1)}},
        {'nested': {'x' * (emission_module._MAX_METADATA_KEY_LENGTH + 1): 1}},
        {'nested': (1, 2)},
        {'nested': {1, 2}},
        {'nan': float('nan')},
        {'inf': float('inf')},
        {'payload': object()},
        {'body': b'bytes'},
        {'nested': {'a': {'b': {'c': {'d': {'e': {'f': {'g': {'h': 1}}}}}}}}},
        {'nested': {f'k{i}': [i for i in range(93)] for i in range(22)}},
    ],
)
def test_artifact_emission_metadata_validation_rejects_invalid_values(metadata: dict[str, object]) -> None:
    with pytest.raises(ArtifactSerializationContractError):
        ArtifactEmissionRequest(
            slot='final-report',
            occurrence=None,
            body=b'body',
            content_type='application/json',
            metadata=metadata,
        )


def test_artifact_emission_identity_and_signature_are_deterministic() -> None:
    context = ArtifactEmissionContext(run_id=123)
    request = ArtifactEmissionRequest(
        slot='final-report',
        occurrence='0001',
        body=b'body',
        content_type='application/json',
        metadata={'kind': 'report', 'nested': {'index': 1}},
    )
    retry_request = ArtifactEmissionRequest(
        slot='final-report',
        occurrence='0001',
        body=b'body',
        content_type='application/json',
        metadata={'nested': {'index': 1}, 'kind': 'report'},
    )
    different_body = ArtifactEmissionRequest(
        slot='final-report',
        occurrence='0001',
        body=b'changed',
        content_type='application/json',
        metadata={'kind': 'report', 'nested': {'index': 1}},
    )

    identity = build_artifact_identity(context=context, request=request)

    assert identity == ArtifactIdentity(run_id=123, slot='final-report', occurrence='0001')
    assert artifact_emission_request_signature(context, request) == artifact_emission_request_signature(context, retry_request)
    assert artifact_emission_requests_equivalent(request, retry_request)
    assert not artifact_emission_requests_equivalent(request, different_body)
    assert build_artifact_identity(context=context, request=request) == build_artifact_identity(context=context, request=retry_request)
    assert build_artifact_identity(context=context, request=request) != build_artifact_identity(context=ArtifactEmissionContext(run_id=124), request=request)


def test_artifact_emission_storage_key_is_deterministic_and_safe() -> None:
    identity = ArtifactIdentity(run_id=123, slot='generated-image', occurrence='revenue-chart')
    storage_key = build_artifact_storage_key(identity)

    assert storage_key == build_artifact_storage_key(identity)
    assert is_safe_storage_key(storage_key)
    assert storage_key == 'artifact/v1/123/generated-image/revenue-chart'


def test_artifact_emission_duplicate_and_conflict_validation() -> None:
    identity = ArtifactIdentity(run_id=123, slot='final-report', occurrence=None)
    existing = ArtifactEmissionRequest(slot='final-report', occurrence=None, body=b'body', content_type='application/json', metadata={'kind': 'report'})
    incoming = ArtifactEmissionRequest(slot='final-report', occurrence=None, body=b'body', content_type='application/json', metadata={'kind': 'report'})
    conflict = ArtifactEmissionRequest(slot='final-report', occurrence=None, body=b'changed', content_type='application/json', metadata={'kind': 'report'})

    validate_duplicate_emission(identity=identity, existing=existing, incoming=incoming)

    with pytest.raises(ArtifactEmissionConflict):
        validate_duplicate_emission(identity=identity, existing=existing, incoming=conflict)


def test_artifact_emission_write_mapping_is_deterministic_and_run_owned() -> None:
    context = ArtifactEmissionContext(run_id=123)
    request = ArtifactEmissionRequest(
        slot='final-report',
        occurrence='0001',
        body=b'body',
        content_type='application/json',
        metadata={'kind': 'report', 'nested': {'index': 1}},
    )
    artifact_request = build_artifact_write_request(context=context, request=request)

    assert isinstance(artifact_request, ArtifactWriteRequest)
    assert artifact_request.run_id == 123
    assert artifact_request.body == b'body'
    assert artifact_request.content_type == 'application/json'
    assert artifact_request.name == 'final-report'
    assert artifact_request.kind == 'artifact'
    assert artifact_request.storage_key == 'artifact/v1/123/final-report/0001'
    assert is_safe_storage_key(artifact_request.storage_key)
    assert artifact_request.metadata['kind'] == 'report'
    assert artifact_request.metadata['nested']['index'] == 1


def test_artifact_emission_module_has_no_random_time_or_store_dependency() -> None:
    module_path = Path('src/cobalt_wren/integrations/artifact/emission.py')
    text = module_path.read_text()

    for token in ('import uuid', 'import random', 'from datetime', 'uuid4(', 'random.', 'datetime.now', 'time.now', 'ArtifactStore(', 'MemoryArtifactStore(', 'FilesystemArtifactStore('):
        assert token not in text
    assert 'ArtifactEmissionRequest' in text
    assert 'ArtifactWriteRequest' not in text


def test_artifact_emission_module_stays_pure_and_store_independent() -> None:
    import cobalt_wren.integrations.artifact.emission as emission_module_runtime

    signature = inspect.signature(emission_module_runtime.build_artifact_identity)
    assert tuple(signature.parameters) == ('context', 'request')
    write_signature = inspect.signature(build_artifact_write_request)
    assert tuple(write_signature.parameters) == ('context', 'request')
    assert 'run_id' not in write_signature.parameters
    assert 'attempt_id' not in write_signature.parameters
    assert 'ArtifactStore' not in emission_module_runtime.__doc__
    assert 'build_artifact_storage_key' in emission_module_runtime.__all__
    assert 'ArtifactWriteRequest' not in emission_module_runtime.__all__
