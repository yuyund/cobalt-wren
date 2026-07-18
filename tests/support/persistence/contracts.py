"""Reusable black-box contract assertions for persistence stores."""

from __future__ import annotations

import pytest

from langgraph_automation.api.errors import (
    ArtifactConflictError,
    ArtifactIntegrityError,
    ArtifactValidationError,
    CheckpointConflictError,
    CheckpointIntegrityError,
    CheckpointValidationError,
)
from langgraph_automation.core.redaction import REDACTED_VALUE
from langgraph_automation.integrations.artifact.base import ArtifactReadResult, ArtifactStore, ArtifactWriteRequest
from langgraph_automation.integrations.checkpoint.base import CheckpointReadResult, CheckpointStore, CheckpointWriteRequest, StoredCheckpoint


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


def _checkpoint_request(
    *,
    run_id: int | str,
    checkpoint_id: str,
    body: bytes,
    parent_checkpoint_id: str | None,
    checkpoint_namespace: str = '',
    serializer_name: str = 'langgraph-json',
    serializer_version: int = 1,
    content_type: str = 'application/vnd.langgraph.checkpoint+json',
    metadata: dict[str, object] | None = None,
) -> CheckpointWriteRequest:
    return CheckpointWriteRequest(
        run_id=run_id,
        checkpoint_namespace=checkpoint_namespace,
        checkpoint_id=checkpoint_id,
        parent_checkpoint_id=parent_checkpoint_id,
        body=body,
        serializer_name=serializer_name,
        serializer_version=serializer_version,
        content_type=content_type,
        metadata={} if metadata is None else metadata,
    )


def assert_checkpoint_versioned_round_trip(store: CheckpointStore) -> None:
    genesis = _checkpoint_request(run_id=123, checkpoint_id='checkpoint-a', parent_checkpoint_id=None, body=b'genesis', checkpoint_namespace='default', metadata={'phase': 'genesis'})
    append = _checkpoint_request(run_id=123, checkpoint_id='checkpoint-b', parent_checkpoint_id='checkpoint-a', body=b'append', checkpoint_namespace='default', metadata={'phase': 'append'})

    written_a = store.save(genesis)
    written_b = store.save(append)
    latest = store.load_latest(123, checkpoint_namespace='default')
    specific_a = store.load_checkpoint(123, 'checkpoint-a', checkpoint_namespace='default')
    specific_b = store.load_checkpoint(123, 'checkpoint-b', checkpoint_namespace='default')
    history = store.list_for_run(123, checkpoint_namespace='default')

    assert written_a.revision == 1
    assert written_b.revision == 2
    assert latest is not None
    assert isinstance(latest, CheckpointReadResult)
    assert latest.checkpoint == written_b
    assert latest.body == b'append'
    assert specific_a is not None
    assert specific_a.checkpoint == written_a
    assert specific_a.body == b'genesis'
    assert specific_b is not None
    assert specific_b.checkpoint == written_b
    assert [item.revision for item in history] == [1, 2]
    assert [item.checkpoint_id for item in history] == ['checkpoint-a', 'checkpoint-b']


def assert_checkpoint_validation_contract() -> None:
    invalid_cases = (
        ({'run_id': True, 'checkpoint_namespace': '', 'checkpoint_id': 'checkpoint-a', 'parent_checkpoint_id': None, 'body': b'body', 'serializer_name': 'langgraph-json', 'serializer_version': 1, 'content_type': 'application/vnd.langgraph.checkpoint+json'}, 'run identifier'),
        ({'run_id': 1, 'checkpoint_namespace': ' default ', 'checkpoint_id': 'checkpoint-a', 'parent_checkpoint_id': None, 'body': b'body', 'serializer_name': 'langgraph-json', 'serializer_version': 1, 'content_type': 'application/vnd.langgraph.checkpoint+json'}, 'checkpoint namespace'),
        ({'run_id': 1, 'checkpoint_namespace': '', 'checkpoint_id': ' checkpoint-a ', 'parent_checkpoint_id': None, 'body': b'body', 'serializer_name': 'langgraph-json', 'serializer_version': 1, 'content_type': 'application/vnd.langgraph.checkpoint+json'}, 'checkpoint identifier'),
        ({'run_id': 1, 'checkpoint_namespace': '', 'checkpoint_id': 'checkpoint-a', 'parent_checkpoint_id': None, 'body': 'body', 'serializer_name': 'langgraph-json', 'serializer_version': 1, 'content_type': 'application/vnd.langgraph.checkpoint+json'}, 'checkpoint body'),
        ({'run_id': 1, 'checkpoint_namespace': '', 'checkpoint_id': 'checkpoint-a', 'parent_checkpoint_id': None, 'body': b'body', 'serializer_name': 'langgraph.json', 'serializer_version': 1, 'content_type': 'application/vnd.langgraph.checkpoint+json'}, 'serializer name'),
        ({'run_id': 1, 'checkpoint_namespace': '', 'checkpoint_id': 'checkpoint-a', 'parent_checkpoint_id': None, 'body': b'body', 'serializer_name': 'langgraph-json', 'serializer_version': 0, 'content_type': 'application/vnd.langgraph.checkpoint+json'}, 'serializer version'),
        ({'run_id': 1, 'checkpoint_namespace': '', 'checkpoint_id': 'checkpoint-a', 'parent_checkpoint_id': None, 'body': b'body', 'serializer_name': 'langgraph-json', 'serializer_version': 1, 'content_type': ' text/plain '}, 'content type'),
        ({'run_id': 1, 'checkpoint_namespace': '', 'checkpoint_id': 'checkpoint-a', 'parent_checkpoint_id': 'checkpoint-a', 'body': b'body', 'serializer_name': 'langgraph-json', 'serializer_version': 1, 'content_type': 'application/vnd.langgraph.checkpoint+json'}, 'self-parent'),
    )

    for kwargs, marker in invalid_cases:
        with pytest.raises(CheckpointValidationError) as exc_info:
            CheckpointWriteRequest(**kwargs)
        assert 'checkpoint store rejected' in str(exc_info.value).lower()


def assert_checkpoint_integrity_error_is_representable() -> None:
    error = CheckpointIntegrityError('Checkpoint store detected an integrity failure.', code='CHECKPOINT_STORE_INTEGRITY_FAILURE')
    assert error.safe_message == 'Checkpoint store detected an integrity failure.'
    assert error.code == 'CHECKPOINT_STORE_INTEGRITY_FAILURE'


def assert_checkpoint_missing_behavior(store: CheckpointStore) -> None:
    assert store.load_latest(404) is None
    assert store.load_checkpoint(404, 'checkpoint-missing') is None
    assert store.list_for_run(404) == []


def assert_checkpoint_run_isolation(store: CheckpointStore) -> None:
    store.save(_checkpoint_request(run_id=1, checkpoint_id='checkpoint-a', parent_checkpoint_id=None, body=b'a', metadata={'stream': 1}))
    store.save(_checkpoint_request(run_id=2, checkpoint_id='checkpoint-b', parent_checkpoint_id=None, body=b'b', metadata={'stream': 2}))

    assert store.load_latest(1).checkpoint.run_id == 1
    assert store.load_latest(2).checkpoint.run_id == 2


def assert_checkpoint_namespace_isolation(store: CheckpointStore) -> None:
    store.save(_checkpoint_request(run_id=9, checkpoint_id='checkpoint-a', parent_checkpoint_id=None, body=b'ns-a', checkpoint_namespace='alpha'))
    store.save(_checkpoint_request(run_id=9, checkpoint_id='checkpoint-a', parent_checkpoint_id=None, body=b'ns-b', checkpoint_namespace='beta'))

    assert store.load_latest(9, checkpoint_namespace='alpha').body == b'ns-a'
    assert store.load_latest(9, checkpoint_namespace='beta').body == b'ns-b'


def assert_checkpoint_defensive_copy(store: CheckpointStore) -> None:
    metadata = {'phase': 'planner', 'nested': {'token': 'abc123'}, 'items': [1, 2, 3]}
    request = _checkpoint_request(run_id=7, checkpoint_id='checkpoint-copy', parent_checkpoint_id=None, body=b'copy', metadata=metadata)

    store.save(request)
    metadata['nested']['token'] = 'changed'
    metadata['items'].append(4)

    loaded = store.load_latest(7)
    assert loaded is not None
    assert loaded.checkpoint.metadata['nested']['token'] == REDACTED_VALUE
    assert loaded.checkpoint.metadata['items'] == [1, 2, 3]

    loaded.checkpoint.metadata['nested']['token'] = 'mutated'
    loaded.checkpoint.metadata['items'].append(5)

    round_trip = store.load_checkpoint(7, 'checkpoint-copy')
    assert round_trip is not None
    assert round_trip.checkpoint.metadata['nested']['token'] == REDACTED_VALUE
    assert round_trip.checkpoint.metadata['items'] == [1, 2, 3]


def assert_checkpoint_idempotency_and_conflict(store: CheckpointStore) -> None:
    genesis = _checkpoint_request(run_id=7, checkpoint_id='checkpoint-a', parent_checkpoint_id=None, body=b'hello', checkpoint_namespace='default', metadata={'phase': 'genesis'})
    written = store.save(genesis)

    same_request = _checkpoint_request(run_id=7, checkpoint_id='checkpoint-a', parent_checkpoint_id=None, body=b'hello', checkpoint_namespace='default', metadata={'phase': 'genesis'})
    same_written = store.save(same_request)
    assert same_written == written

    conflict_inputs = (
        _checkpoint_request(run_id=7, checkpoint_id='checkpoint-a', parent_checkpoint_id=None, body=b'hello-2', checkpoint_namespace='default', metadata={'phase': 'genesis'}),
        _checkpoint_request(run_id=7, checkpoint_id='checkpoint-a', parent_checkpoint_id='checkpoint-x', body=b'hello', checkpoint_namespace='default', metadata={'phase': 'genesis'}),
        _checkpoint_request(run_id=7, checkpoint_id='checkpoint-a', parent_checkpoint_id=None, body=b'hello', checkpoint_namespace='default', serializer_name='langgraph-json-2', metadata={'phase': 'genesis'}),
        _checkpoint_request(run_id=7, checkpoint_id='checkpoint-a', parent_checkpoint_id=None, body=b'hello', checkpoint_namespace='default', content_type='application/vnd.langgraph.checkpoint+msgpack', metadata={'phase': 'genesis'}),
        _checkpoint_request(run_id=7, checkpoint_id='checkpoint-a', parent_checkpoint_id=None, body=b'hello', checkpoint_namespace='default', metadata={'phase': 'changed'}),
    )
    for request in conflict_inputs:
        with pytest.raises(CheckpointConflictError):
            store.save(request)
        assert store.load_checkpoint(7, 'checkpoint-a', checkpoint_namespace='default') is not None


def assert_checkpoint_descriptor_derivation(store: CheckpointStore) -> None:
    request = _checkpoint_request(
        run_id=11,
        checkpoint_id='checkpoint-size',
        parent_checkpoint_id=None,
        body=b'checkpoint-body',
        checkpoint_namespace='default',
        serializer_name='langgraph-json',
        serializer_version=2,
        content_type='application/vnd.langgraph.checkpoint+json',
    )
    written = store.save(request)
    read = store.load_checkpoint(11, 'checkpoint-size', checkpoint_namespace='default')

    assert written.size == len(b'checkpoint-body')
    assert written.digest.startswith('sha256:')
    assert written.serializer_name == 'langgraph-json'
    assert written.serializer_version == 2
    assert written.content_type == 'application/vnd.langgraph.checkpoint+json'
    assert read is not None
    assert read.checkpoint.size == written.size
    assert read.checkpoint.digest == written.digest
    assert read.body == b'checkpoint-body'


def assert_checkpoint_diagnostic_non_exposure(store: CheckpointStore) -> None:
    request = _checkpoint_request(
        run_id=1,
        checkpoint_id='checkpoint-diagnostic',
        parent_checkpoint_id=None,
        body=b'SUPER_SECRET_BODY_SENTINEL',
        checkpoint_namespace='default',
        metadata={'secret': 'SUPER_SECRET_METADATA_SENTINEL', 'path': '/tmp/secret.txt'},
    )
    written = store.save(request)
    read = store.load_checkpoint(1, 'checkpoint-diagnostic', checkpoint_namespace='default')
    assert read is not None

    for text in (repr(request), repr(written), repr(read)):
        assert 'SUPER_SECRET_BODY_SENTINEL' not in text
        assert 'SUPER_SECRET_METADATA_SENTINEL' not in text
        assert '/tmp/secret.txt' not in text
        assert 'token' not in text.lower()
        assert 'secret' not in text.lower()
        assert 'authorization' not in text.lower()


def assert_checkpoint_concurrent_append(store_factory) -> None:
    from threading import Barrier, Thread

    store = store_factory()
    genesis = _checkpoint_request(run_id=21, checkpoint_id='checkpoint-a', parent_checkpoint_id=None, body=b'genesis', checkpoint_namespace='default')
    store.save(genesis)

    barrier = Barrier(3)
    results: list[object] = []

    def _worker(checkpoint_id: str, body: bytes) -> None:
        barrier.wait()
        try:
            results.append(store.save(_checkpoint_request(run_id=21, checkpoint_id=checkpoint_id, parent_checkpoint_id='checkpoint-a', body=body, checkpoint_namespace='default')))
        except CheckpointConflictError as exc:
            results.append(exc)

    threads = [Thread(target=_worker, args=('checkpoint-b', b'b')), Thread(target=_worker, args=('checkpoint-c', b'c'))]
    for thread in threads:
        thread.start()
    barrier.wait()
    for thread in threads:
        thread.join()

    success_count = sum(1 for item in results if isinstance(item, StoredCheckpoint))
    conflict_count = sum(1 for item in results if isinstance(item, CheckpointConflictError))
    assert success_count == 1
    assert conflict_count == 1
    assert [item.revision for item in store.list_for_run(21, checkpoint_namespace='default')] == [1, 2]
