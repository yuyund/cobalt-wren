"""Contract tests for explicit artifact emission identity."""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from langgraph_automation.core.redaction import REDACTED_VALUE
from langgraph_automation.integrations.artifact.emission import (
    ArtifactEmissionContext,
    ArtifactEmissionRequest,
    ArtifactIdentity,
    ArtifactOccurrence,
    ArtifactSlot,
    ArtifactOccurrenceError,
    ArtifactSerializationContractError,
    ArtifactSlotError,
    artifact_emission_request_signature,
    build_artifact_identity,
    build_artifact_storage_key,
    normalize_artifact_occurrence,
    normalize_artifact_slot,
)
from langgraph_automation.integrations.artifact.keys import is_safe_storage_key


def test_artifact_emission_request_fields_are_explicit_and_body_aware() -> None:
    assert tuple(ArtifactEmissionRequest.__dataclass_fields__) == ('slot', 'body', 'occurrence', 'content_type', 'metadata')
    assert tuple(ArtifactIdentity.__dataclass_fields__) == ('run_id', 'slot', 'occurrence')
    assert tuple(ArtifactSlot.__dataclass_fields__) == ('value',)
    assert tuple(ArtifactOccurrence.__dataclass_fields__) == ('value',)
    assert tuple(ArtifactEmissionContext.__dataclass_fields__) == ('run_id',)
    assert ArtifactEmissionRequest.__dataclass_fields__['body'].repr is False
    assert ArtifactEmissionRequest.__dataclass_fields__['metadata'].repr is False


@pytest.mark.parametrize(
    ('slot', 'occurrence'),
    [
        ('final-report', None),
        ('summary', '0001'),
        ('generated-image', 'revenue-chart'),
        ('export-001', ArtifactOccurrence('batch-1')),
    ],
)
def test_artifact_emission_identity_validation_accepts_canonical_values(
    slot: str | ArtifactSlot,
    occurrence: str | ArtifactOccurrence | None,
) -> None:
    identity = build_artifact_identity(run_id=' 123 ', slot=slot, occurrence=occurrence)

    assert identity.run_id == '123'
    assert identity.slot == normalize_artifact_slot(slot)
    if occurrence is None:
        assert identity.occurrence is None
    else:
        assert identity.occurrence == normalize_artifact_occurrence(occurrence)


@pytest.mark.parametrize('bad_slot', ['', ' ', 'Final Report', '../report', '/report', 'report/slot', 'report\u0000', 'slot_1', 'slot/../x'])
def test_artifact_slot_validation_rejects_non_canonical_values(bad_slot: str) -> None:
    with pytest.raises(ArtifactSlotError):
        ArtifactSlot(bad_slot)


@pytest.mark.parametrize('bad_occurrence', ['', ' ', 'Run #1', '../occurrence', '/occurrence', 'occurrence/slot', 'occurrence\u0000', 'occurrence_1'])
def test_artifact_occurrence_validation_rejects_non_canonical_values(bad_occurrence: str) -> None:
    with pytest.raises(ArtifactOccurrenceError):
        ArtifactOccurrence(bad_occurrence)


def test_artifact_emission_request_defensively_copies_and_normalizes_input() -> None:
    metadata = {
        'token': 'Authorization: Bearer secret-token /tmp/secret.txt',
        'nested': {'path': '/tmp/secret.txt'},
        'items': [1, 2, 3],
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
    metadata['items'].append(4)
    metadata['token'] = 'changed'

    assert request.body == b'hello world'
    assert request.content_type == 'text/plain; charset=utf-8'
    assert request.metadata['token'] == REDACTED_VALUE
    assert request.metadata['nested']['path'] == REDACTED_VALUE
    assert request.metadata['items'] == [1, 2, 3]


@pytest.mark.parametrize(
    'metadata',
    [
        {'nan': float('nan')},
        {'inf': float('inf')},
        {'payload': object()},
        {'body': b'bytes'},
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


def test_artifact_emission_signature_is_deterministic_for_retry_and_distinct_for_rerun() -> None:
    first_run_context = ArtifactEmissionContext(run_id=123)
    retry_context = ArtifactEmissionContext(run_id=123)
    rerun_context = ArtifactEmissionContext(run_id=124)

    request = ArtifactEmissionRequest(
        slot='final-report',
        occurrence=None,
        body=b'body',
        content_type='application/json',
        metadata={'kind': 'report', 'nested': {'index': 1}},
    )
    retry_request = ArtifactEmissionRequest(
        slot='final-report',
        occurrence=None,
        body=b'body',
        content_type='application/json',
        metadata={'nested': {'index': 1}, 'kind': 'report'},
    )

    assert artifact_emission_request_signature(first_run_context, request) == artifact_emission_request_signature(retry_context, retry_request)
    assert artifact_emission_request_signature(rerun_context, request) != artifact_emission_request_signature(first_run_context, request)
    assert build_artifact_identity(run_id=123, slot='final-report', occurrence=None) == build_artifact_identity(run_id=123, slot='final-report', occurrence=None)
    assert build_artifact_identity(run_id=123, slot='final-report', occurrence='0001') != build_artifact_identity(run_id=123, slot='final-report', occurrence='0002')


def test_artifact_storage_key_is_deterministic_and_safe() -> None:
    identity = build_artifact_identity(run_id='run-123', slot='generated-image', occurrence='revenue-chart')
    storage_key = build_artifact_storage_key(identity)

    assert storage_key == build_artifact_storage_key(identity)
    assert is_safe_storage_key(storage_key)
    assert storage_key.startswith('artifact/v1/')


def test_artifact_emission_module_has_no_random_or_time_dependency() -> None:
    module_path = Path('src/langgraph_automation/integrations/artifact/emission.py')
    text = module_path.read_text()

    for token in ('import uuid', 'import random', 'from datetime', 'uuid4(', 'random.', 'datetime.now', 'time.now'):
        assert token not in text
    assert 'ArtifactSerializationContractError' in text


def test_artifact_emission_module_stays_pure_and_store_independent() -> None:
    import langgraph_automation.integrations.artifact.emission as emission_module

    signature = inspect.signature(emission_module.build_artifact_identity)
    assert tuple(signature.parameters) == ('run_id', 'slot', 'occurrence')
    assert 'ArtifactStore' not in emission_module.__doc__
    assert 'build_artifact_storage_key' in emission_module.__all__
