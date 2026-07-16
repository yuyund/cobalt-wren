"""Reusable black-box contract assertions for persistence stores."""

from __future__ import annotations

import pytest

from langgraph_automation.api.errors import ArtifactConflictError, ArtifactIntegrityError, ArtifactValidationError
from langgraph_automation.core.redaction import REDACTED_VALUE
from langgraph_automation.integrations.artifact.base import ArtifactReadResult, ArtifactStore, ArtifactWriteRequest
from langgraph_automation.integrations.checkpoint.base import CheckpointStore


def assert_artifact_round_trip(store: ArtifactStore) -> None:
    request = ArtifactWriteRequest(
        run_id=123,
        storage_key='run-123/report.md',
        body=b'hello world',
        name='report',
        kind='text',
        content_type='text/markdown',
        metadata={'run_id': 123, 'phase': 'run', 'nested': {'value': 'keep-me'}},
    )

    written = store.put(request)
    fetched = store.get('run-123/report.md')

    assert fetched is not None
    assert isinstance(fetched, ArtifactReadResult)
    assert fetched.artifact == written
    assert fetched.body == request.body
    assert written.size == len(request.body)
    assert written.digest.startswith('sha256:')
    assert fetched.artifact.digest == written.digest
    assert fetched.artifact.metadata == request.metadata


def assert_artifact_missing_behavior(store: ArtifactStore) -> None:
    assert store.get('missing/report.md') is None
    assert store.list_for_run(404) == []


def assert_artifact_run_isolation(store: ArtifactStore) -> None:
    run_a = ArtifactWriteRequest(run_id=1, storage_key='run-1/a.md', body=b'a', name='a', kind='text', metadata={'run_id': 1})
    run_b = ArtifactWriteRequest(run_id=2, storage_key='run-2/b.md', body=b'b', name='b', kind='text', metadata={'run_id': 2})
    written_a = store.put(run_a)
    written_b = store.put(run_b)

    assert [item.storage_key for item in store.list_for_run(1)] == ['run-1/a.md']
    assert [item.storage_key for item in store.list_for_run(2)] == ['run-2/b.md']
    assert written_a.storage_key != written_b.storage_key


def assert_artifact_defensive_copy(store: ArtifactStore) -> None:
    metadata = {'run_id': 9, 'nested': {'token': 'abc123'}, 'items': [1, 2, 3]}
    request = ArtifactWriteRequest(run_id=9, storage_key='run-9/copy.md', body=b'copy', name='copy', kind='text', metadata=metadata)

    store.put(request)
    metadata['nested']['token'] = 'changed'
    metadata['items'].append(4)

    fetched = store.get('run-9/copy.md')
    assert fetched is not None
    assert fetched.artifact.metadata['nested']['token'] == REDACTED_VALUE
    assert fetched.artifact.metadata['items'] == [1, 2, 3]

    fetched.artifact.metadata['nested']['token'] = 'mutated'
    fetched.artifact.metadata['items'].append(5)

    round_trip = store.get('run-9/copy.md')
    assert round_trip is not None
    assert round_trip.artifact.metadata['nested']['token'] == REDACTED_VALUE
    assert round_trip.artifact.metadata['items'] == [1, 2, 3]


def assert_artifact_safe_reference_rejected(store: ArtifactStore) -> None:
    unsafe_keys = (
        '/tmp/output.md',
        '../secret.txt',
        'https://example.invalid/artifacts/report.md',
        'token:example/output.md',
    )
    for storage_key in unsafe_keys:
        with pytest.raises(ArtifactValidationError) as exc_info:
            store.put(
                ArtifactWriteRequest(
                    run_id=1,
                    storage_key=storage_key,
                    body=b'report',
                    name='report',
                    kind='text',
                )
            )
        text = str(exc_info.value)
        assert storage_key not in text
        assert 'secret' not in text.lower()
        assert 'token' not in text.lower()
        assert 'authorization' not in text.lower()
        assert '/tmp' not in text


def assert_artifact_diagnostic_non_exposure(store: ArtifactStore) -> None:
    request = ArtifactWriteRequest(
        run_id=1,
        storage_key='run-1/diagnostic.md',
        body=b'SUPER_SECRET_BODY_SENTINEL',
        name='report',
        kind='text',
        metadata={'secret': 'SUPER_SECRET_METADATA_SENTINEL', 'path': '/tmp/secret.txt'},
    )
    written = store.put(request)
    fetched = store.get('run-1/diagnostic.md')
    assert fetched is not None

    for text in (repr(request), repr(written), repr(fetched)):
        assert 'SUPER_SECRET_BODY_SENTINEL' not in text
        assert 'SUPER_SECRET_METADATA_SENTINEL' not in text
        assert '/tmp/secret.txt' not in text
        assert 'token' not in text.lower()
        assert 'secret' not in text.lower()
        assert 'authorization' not in text.lower()


def assert_artifact_idempotency_and_conflict(store: ArtifactStore) -> None:
    base = ArtifactWriteRequest(
        run_id=7,
        storage_key='run-7/report.md',
        body=b'hello',
        name='report',
        kind='text',
        content_type='text/markdown',
        metadata={'phase': 'run', 'nested': {'value': 'keep-me'}},
    )
    written = store.put(base)

    same_request = ArtifactWriteRequest(
        run_id=7,
        storage_key='run-7/report.md',
        body=b'hello',
        name='report',
        kind='text',
        content_type='text/markdown',
        metadata={'nested': {'value': 'keep-me'}, 'phase': 'run'},
    )
    same_written = store.put(same_request)
    assert same_written == written
    assert store.get('run-7/report.md').artifact == written

    conflict_inputs = (
        ArtifactWriteRequest(run_id=7, storage_key='run-7/report.md', body=b'hello-2', name='report', kind='text', content_type='text/markdown', metadata={'phase': 'run'}),
        ArtifactWriteRequest(run_id=8, storage_key='run-7/report.md', body=b'hello', name='report', kind='text', content_type='text/markdown', metadata={'phase': 'run'}),
        ArtifactWriteRequest(run_id=7, storage_key='run-7/report.md', body=b'hello', name='report', kind='text', content_type='application/json', metadata={'phase': 'run'}),
        ArtifactWriteRequest(run_id=7, storage_key='run-7/report.md', body=b'hello', name='report', kind='text', content_type='text/markdown', metadata={'phase': 'changed'}),
    )
    for request in conflict_inputs:
        with pytest.raises(ArtifactConflictError):
            store.put(request)
        assert store.get('run-7/report.md').artifact == written


def assert_artifact_integrity_errors_are_representable() -> None:
    error = ArtifactIntegrityError('Artifact store detected an integrity failure.', code='ARTIFACT_STORE_INTEGRITY_FAILURE')
    assert error.safe_message == 'Artifact store detected an integrity failure.'
    assert error.code == 'ARTIFACT_STORE_INTEGRITY_FAILURE'


def assert_artifact_storage_value_copy(store: ArtifactStore) -> None:
    request = ArtifactWriteRequest(
        run_id=11,
        storage_key='run-11/list.md',
        body=b'list body',
        name='list',
        kind='text',
        metadata={'nested': {'token': 'abc123'}},
    )
    store.put(request)
    listed = store.list_for_run(11)
    assert listed
    listed[0].metadata['nested']['token'] = 'mutated'
    fetched = store.get('run-11/list.md')
    assert fetched is not None
    assert fetched.artifact.metadata['nested']['token'] == REDACTED_VALUE


def assert_artifact_digest_and_size(store: ArtifactStore) -> None:
    request = ArtifactWriteRequest(run_id=12, storage_key='run-12/digest.md', body=b'hello digest', name='digest', kind='text')
    written = store.put(request)
    assert written.size == len(b'hello digest')
    assert written.digest.startswith('sha256:')
    read = store.get('run-12/digest.md')
    assert read is not None
    assert read.artifact.size == written.size
    assert read.artifact.digest == written.digest


def assert_artifact_list_order_is_deterministic(store: ArtifactStore) -> None:
    store.put(ArtifactWriteRequest(run_id=13, storage_key='run-13/b.md', body=b'b', name='b', kind='text'))
    store.put(ArtifactWriteRequest(run_id=13, storage_key='run-13/a.md', body=b'a', name='a', kind='text'))
    assert [artifact.storage_key for artifact in store.list_for_run(13)] == ['run-13/a.md', 'run-13/b.md']


def assert_artifact_safe_storage_key_validation(store: ArtifactStore) -> None:
    with pytest.raises(ArtifactValidationError):
        store.put(ArtifactWriteRequest(run_id=1, storage_key='/tmp/output.md', body=b'report', name='report', kind='text'))


def assert_artifact_read_result_repr_safety(store: ArtifactStore) -> None:
    request = ArtifactWriteRequest(
        run_id=14,
        storage_key='run-14/repr.md',
        body=b'SUPER_SECRET_BODY_SENTINEL',
        name='repr',
        kind='text',
        metadata={'token': 'SUPER_SECRET_METADATA_SENTINEL'},
    )
    store.put(request)
    result = store.get('run-14/repr.md')
    assert result is not None
    text = repr(result)
    assert 'SUPER_SECRET_BODY_SENTINEL' not in text
    assert 'SUPER_SECRET_METADATA_SENTINEL' not in text


def assert_checkpoint_round_trip(store: CheckpointStore) -> None:
    state = {'phase': 'planner', 'nested': {'value': 'keep-me'}}
    written = store.save(7, state, thread_id='thread-7', checkpoint_namespace='default', backend='memory', node_name='planner')
    loaded = store.load(7)

    assert loaded is not None
    assert loaded == state
    assert written.thread_id == 'thread-7'
    assert written.checkpoint_namespace == 'default'
    assert written.backend == 'memory'
    assert written.node_name == 'planner'


def assert_checkpoint_missing_behavior(store: CheckpointStore) -> None:
    assert store.load(404) is None


def assert_checkpoint_run_isolation(store: CheckpointStore) -> None:
    store.save(1, {'phase': 'a'}, thread_id='thread-a', node_name='planner')
    store.save(2, {'phase': 'b'}, thread_id='thread-b', node_name='planner')

    assert store.load(1) == {'phase': 'a'}
    assert store.load(2) == {'phase': 'b'}


def assert_checkpoint_defensive_copy(store: CheckpointStore) -> None:
    state = {'phase': 'planner', 'nested': {'token': 'abc123'}, 'items': [1, 2, 3]}
    store.save(9, state, thread_id='thread-9', node_name='planner')
    state['nested']['token'] = 'changed'
    state['items'].append(4)

    loaded = store.load(9)
    assert loaded is not None
    assert loaded['nested']['token'] == 'abc123'
    assert loaded['items'] == [1, 2, 3]

    loaded['nested']['token'] = 'mutated'
    loaded['items'].append(5)

    round_trip = store.load(9)
    assert round_trip is not None
    assert round_trip['nested']['token'] == 'abc123'
    assert round_trip['items'] == [1, 2, 3]


def assert_checkpoint_delete_contract(store: CheckpointStore) -> None:
    store.save(11, {'phase': 'delete'}, thread_id='thread-11', node_name='planner')
    store.delete(11)
    assert store.load(11) is None
    assert store.delete(404) is None


def assert_checkpoint_latest_state_compatibility(store: CheckpointStore) -> None:
    store.save(12, {'phase': 'first'}, thread_id='thread-12', node_name='planner')
    store.save(12, {'phase': 'second'}, thread_id='thread-12', node_name='planner')
    assert store.load(12) == {'phase': 'second'}


def assert_checkpoint_diagnostic_non_exposure(store: CheckpointStore) -> None:
    state = {'secret': 'token', 'path': '/tmp/secret.txt'}
    result = store.save(13, state, thread_id='thread-13', node_name='planner')
    assert 'token' not in result.state_summary.lower()
    assert '/tmp/secret.txt' not in result.state_summary
