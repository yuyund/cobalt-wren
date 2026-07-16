"""Reusable black-box contract assertions for persistence stores."""

from __future__ import annotations

from langgraph_automation.integrations.artifact.base import ArtifactStore, ArtifactWriteResult
from langgraph_automation.integrations.checkpoint.base import CheckpointStore


def assert_artifact_round_trip(store: ArtifactStore) -> None:
    artifact = ArtifactWriteResult(
        storage_key='run-123/report.md',
        name='report',
        kind='text',
        content_type='text/markdown',
        size=12,
        metadata={'run_id': 123, 'phase': 'run', 'nested': {'value': 'keep-me'}},
    )

    written = store.put(artifact)
    fetched = store.get('run-123/report.md')

    assert fetched is not None
    assert fetched.storage_key == written.storage_key
    assert fetched.name == written.name
    assert fetched.kind == written.kind
    assert fetched.content_type == written.content_type
    assert fetched.size == written.size
    assert fetched.metadata == written.metadata


def assert_artifact_missing_behavior(store: ArtifactStore) -> None:
    assert store.get('missing/report.md') is None
    assert store.list_for_run(404) == []


def assert_artifact_run_isolation(store: ArtifactStore) -> None:
    run_a = ArtifactWriteResult(storage_key='run-1/a.md', name='a', kind='text', metadata={'run_id': 1})
    run_b = ArtifactWriteResult(storage_key='run-2/b.md', name='b', kind='text', metadata={'run_id': 2})
    store.put(run_a)
    store.put(run_b)

    assert [item.storage_key for item in store.list_for_run(1)] == ['run-1/a.md']
    assert [item.storage_key for item in store.list_for_run(2)] == ['run-2/b.md']


def assert_artifact_defensive_copy(store: ArtifactStore) -> None:
    metadata = {'run_id': 9, 'nested': {'token': 'abc123'}, 'items': [1, 2, 3]}
    artifact = ArtifactWriteResult(storage_key='run-9/copy.md', name='copy', kind='text', metadata=metadata)

    store.put(artifact)
    metadata['nested']['token'] = 'changed'
    metadata['items'].append(4)

    fetched = store.get('run-9/copy.md')
    assert fetched is not None
    assert fetched.metadata['nested']['token'] == 'abc123'
    assert fetched.metadata['items'] == [1, 2, 3]

    fetched.metadata['nested']['token'] = 'mutated'
    fetched.metadata['items'].append(5)

    round_trip = store.get('run-9/copy.md')
    assert round_trip is not None
    assert round_trip.metadata['nested']['token'] == 'abc123'
    assert round_trip.metadata['items'] == [1, 2, 3]


def assert_artifact_safe_reference_rejected(store: ArtifactStore) -> None:
    unsafe_keys = (
        '/tmp/output.md',
        '../secret.txt',
        'https://example.invalid/artifacts/report.md',
        'token:example/output.md',
    )
    for storage_key in unsafe_keys:
        artifact = ArtifactWriteResult(storage_key=storage_key, name='report', kind='text')
        try:
            store.put(artifact)
        except ValueError as exc:
            assert storage_key not in str(exc)
            assert 'secret' not in str(exc).lower()
            assert 'token' not in str(exc).lower()
            assert 'authorization' not in str(exc).lower()
            assert '/tmp' not in str(exc)
        else:
            raise AssertionError(f'unsafe storage key was accepted: {storage_key!r}')


def assert_artifact_diagnostic_non_exposure(store: ArtifactStore) -> None:
    artifact = ArtifactWriteResult(
        storage_key='/tmp/secret.txt',
        name='report',
        kind='text',
        metadata={'secret': 'token', 'path': '/tmp/secret.txt'},
    )
    try:
        store.put(artifact)
    except ValueError as exc:
        text = str(exc)
        assert '/tmp/secret.txt' not in text
        assert 'token' not in text.lower()
        assert 'secret' not in text.lower()
        assert 'authorization' not in text.lower()
    else:
        raise AssertionError('unsafe storage key was accepted')


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
