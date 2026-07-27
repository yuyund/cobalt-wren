"""Memory artifact store tests."""

from __future__ import annotations

import pytest

from cobalt_wren.api.errors import ArtifactConflictError
from cobalt_wren.core.redaction import REDACTED_VALUE
from cobalt_wren.integrations.artifact.base import ArtifactReadResult, ArtifactWriteRequest
from cobalt_wren.integrations.artifact.memory_store import MemoryArtifactStore


def test_memory_artifact_store_put_get_and_list_for_run() -> None:
    store = MemoryArtifactStore()
    request = ArtifactWriteRequest(
        run_id=123,
        storage_key='run-123/output.md',
        body=b'hello world',
        name='report',
        kind='text',
        content_type='text/markdown',
        metadata={'run_id': 123, 'phase': 'run'},
    )

    written = store.put(request)
    fetched = store.get('run-123/output.md')

    assert written.storage_key == 'run-123/output.md'
    assert written.size == len(b'hello world')
    assert written.digest.startswith('sha256:')
    assert fetched is not None
    assert isinstance(fetched, ArtifactReadResult)
    assert fetched.artifact == written
    assert fetched.body == b'hello world'
    assert store.list_for_run(123) == [written]


def test_memory_artifact_store_idempotent_write_and_conflict_detection() -> None:
    store = MemoryArtifactStore()
    request = ArtifactWriteRequest(run_id=123, storage_key='run-123/output.md', body=b'hello world', name='report', kind='text', metadata={'phase': 'run'})

    written = store.put(request)
    same_request = ArtifactWriteRequest(run_id=123, storage_key='run-123/output.md', body=b'hello world', name='report', kind='text', metadata={'phase': 'run'})
    same_written = store.put(same_request)

    assert same_written == written

    with pytest.raises(ArtifactConflictError):
        store.put(ArtifactWriteRequest(run_id=123, storage_key='run-123/output.md', body=b'other body', name='report', kind='text', metadata={'phase': 'run'}))

    assert store.get('run-123/output.md').artifact == written


def test_memory_artifact_store_returns_defensive_copies() -> None:
    store = MemoryArtifactStore()
    metadata = {'run_id': 123, 'nested': {'token': 'abc123'}, 'items': [1, 2, 3]}
    request = ArtifactWriteRequest(run_id=123, storage_key='run-123/copy.md', body=b'copy', name='copy', kind='text', metadata=metadata)

    written = store.put(request)
    metadata['nested']['token'] = 'changed'
    metadata['items'].append(4)

    fetched = store.get('run-123/copy.md')
    assert fetched is not None
    fetched.artifact.metadata['nested']['token'] = 'mutated'
    fetched.artifact.metadata['items'].append(5)

    round_trip = store.get('run-123/copy.md')
    assert round_trip is not None
    assert round_trip.artifact.metadata['nested']['token'] == REDACTED_VALUE
    assert round_trip.artifact.metadata['items'] == [1, 2, 3]
    assert written.metadata['nested']['token'] == REDACTED_VALUE


def test_memory_artifact_store_deterministic_list_order() -> None:
    store = MemoryArtifactStore()
    store.put(ArtifactWriteRequest(run_id=7, storage_key='run-7/b.md', body=b'b', name='b', kind='text'))
    store.put(ArtifactWriteRequest(run_id=7, storage_key='run-7/a.md', body=b'a', name='a', kind='text'))
    store.put(ArtifactWriteRequest(run_id=7, storage_key='run-7/c.md', body=b'c', name='c', kind='text'))

    assert [artifact.storage_key for artifact in store.list_for_run(7)] == ['run-7/a.md', 'run-7/b.md', 'run-7/c.md']


def test_memory_artifact_store_repr_hides_body_and_metadata() -> None:
    store = MemoryArtifactStore()
    request = ArtifactWriteRequest(
        run_id=1,
        storage_key='run-1/repr.md',
        body=b'SUPER_SECRET_BODY_SENTINEL',
        name='report',
        kind='text',
        metadata={'token': 'SUPER_SECRET_METADATA_SENTINEL'},
    )
    written = store.put(request)
    result = ArtifactReadResult(artifact=written, body=b'SUPER_SECRET_BODY_SENTINEL')

    assert 'SUPER_SECRET_BODY_SENTINEL' not in repr(request)
    assert 'SUPER_SECRET_METADATA_SENTINEL' not in repr(request)
    assert 'SUPER_SECRET_BODY_SENTINEL' not in repr(written)
    assert 'SUPER_SECRET_METADATA_SENTINEL' not in repr(written)
    assert 'SUPER_SECRET_BODY_SENTINEL' not in repr(result)
    assert 'SUPER_SECRET_METADATA_SENTINEL' not in repr(result)
