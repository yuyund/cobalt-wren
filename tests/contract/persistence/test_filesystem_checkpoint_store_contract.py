"""Filesystem checkpoint store contract coverage."""

from __future__ import annotations

import multiprocessing
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from langgraph_automation.api.errors import CheckpointConflictError, CheckpointIntegrityError
from langgraph_automation.integrations.checkpoint import CheckpointReadResult, CheckpointWriteRequest, FilesystemCheckpointStore, StoredCheckpoint
import langgraph_automation.integrations.checkpoint.filesystem_store as filesystem_store
from tests.support.persistence import FaultPlan, FaultTiming, FaultingCheckpointStore


def _request(
    *,
    run_id: int | str = 1,
    checkpoint_namespace: str = 'default',
    checkpoint_id: str = 'checkpoint-a',
    parent_checkpoint_id: str | None = None,
    body: bytes = b'body-a',
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


def _process_worker(root: str, start: multiprocessing.Event, request_kwargs: dict[str, object], queue: multiprocessing.Queue) -> None:
    try:
        store = FilesystemCheckpointStore(root)
        start.wait(timeout=20)
        written = store.save(CheckpointWriteRequest(**request_kwargs))
    except Exception as exc:  # pragma: no cover - child process path
        queue.put({'status': 'error', 'type': exc.__class__.__name__})
    else:  # pragma: no cover - child process path
        queue.put({'status': 'ok', 'checkpoint_id': written.checkpoint_id, 'revision': written.revision})


def _process_lock_worker(root: str, start: multiprocessing.Event) -> None:
    store = FilesystemCheckpointStore(root)
    stream_key = store._stream_key(1, 'default')
    with store._locked_stream(stream_key):
        start.set()
        os._exit(0)


def _revisions(store: FilesystemCheckpointStore) -> list[int]:
    return [checkpoint.revision for checkpoint in store.list_for_run(1, checkpoint_namespace='default')]


def test_filesystem_checkpoint_store_round_trip_restart_and_append(tmp_path: Path) -> None:
    root = tmp_path / 'checkpoint-store'
    store_a = FilesystemCheckpointStore(root)

    written_a = store_a.save(_request(checkpoint_id='checkpoint-a', body=b'a', metadata={'phase': 'genesis'}))
    written_b = store_a.save(_request(checkpoint_id='checkpoint-b', parent_checkpoint_id='checkpoint-a', body=b'b', metadata={'phase': 'second'}))
    written_c = store_a.save(_request(checkpoint_id='checkpoint-c', parent_checkpoint_id='checkpoint-b', body=b'c', metadata={'phase': 'third'}))

    store_b = FilesystemCheckpointStore(root)
    latest = store_b.load_latest(1, checkpoint_namespace='default')
    specific_a = store_b.load_checkpoint(1, 'checkpoint-a', checkpoint_namespace='default')
    specific_b = store_b.load_checkpoint(1, 'checkpoint-b', checkpoint_namespace='default')
    specific_c = store_b.load_checkpoint(1, 'checkpoint-c', checkpoint_namespace='default')
    history = store_b.list_for_run(1, checkpoint_namespace='default')

    assert latest is not None
    assert isinstance(latest, CheckpointReadResult)
    assert latest.checkpoint == written_c
    assert latest.body == b'c'
    assert specific_a is not None and specific_a.checkpoint == written_a
    assert specific_b is not None and specific_b.checkpoint == written_b
    assert specific_c is not None and specific_c.checkpoint == written_c
    assert _revisions(store_b) == [1, 2, 3]
    assert store_b.save(_request(checkpoint_id='checkpoint-d', parent_checkpoint_id='checkpoint-c', body=b'd')).revision == 4
    assert [checkpoint.revision for checkpoint in history] == [1, 2, 3]
    assert str(root) not in repr(store_b)


def test_filesystem_checkpoint_store_same_instance_thread_concurrency_same_parent(tmp_path: Path) -> None:
    root = tmp_path / 'checkpoint-store'
    store = FilesystemCheckpointStore(root)
    store.save(_request(checkpoint_id='checkpoint-a', body=b'a'))

    barrier = threading.Barrier(2)
    results: list[object] = []

    def worker(checkpoint_id: str, body: bytes) -> None:
        barrier.wait(timeout=5)
        try:
            results.append(store.save(_request(checkpoint_id=checkpoint_id, parent_checkpoint_id='checkpoint-a', body=body)))
        except CheckpointConflictError as exc:
            results.append(exc)

    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(worker, ('checkpoint-b', 'checkpoint-c'), (b'b', b'c')))

    assert sum(1 for item in results if isinstance(item, CheckpointConflictError)) == 1
    assert sum(1 for item in results if hasattr(item, 'revision')) == 1
    assert _revisions(store) == [1, 2]


def test_filesystem_checkpoint_store_separate_instance_thread_concurrency_same_parent(tmp_path: Path) -> None:
    root = tmp_path / 'checkpoint-store'
    FilesystemCheckpointStore(root).save(_request(checkpoint_id='checkpoint-a', body=b'a'))

    barrier = threading.Barrier(2)
    results: list[object] = []

    def worker(checkpoint_id: str, body: bytes) -> None:
        barrier.wait(timeout=5)
        store = FilesystemCheckpointStore(root)
        try:
            results.append(store.save(_request(checkpoint_id=checkpoint_id, parent_checkpoint_id='checkpoint-a', body=body)))
        except CheckpointConflictError as exc:
            results.append(exc)

    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(worker, ('checkpoint-b', 'checkpoint-c'), (b'b', b'c')))

    assert sum(1 for item in results if isinstance(item, CheckpointConflictError)) == 1
    assert sum(1 for item in results if hasattr(item, 'revision')) == 1
    assert _revisions(FilesystemCheckpointStore(root)) == [1, 2]


@pytest.mark.skipif(os.name != 'posix', reason='POSIX advisory locking required')
def test_filesystem_checkpoint_store_process_concurrency_same_parent(tmp_path: Path) -> None:
    root = tmp_path / 'checkpoint-store'
    FilesystemCheckpointStore(root).save(_request(checkpoint_id='checkpoint-a', body=b'a'))

    ctx = multiprocessing.get_context('spawn')
    start = ctx.Event()
    queue: multiprocessing.Queue = ctx.Queue()
    first = {
        'run_id': 1,
        'checkpoint_namespace': 'default',
        'checkpoint_id': 'checkpoint-b',
        'parent_checkpoint_id': 'checkpoint-a',
        'body': b'b',
        'serializer_name': 'langgraph-json',
        'serializer_version': 1,
        'content_type': 'application/vnd.langgraph.checkpoint+json',
        'metadata': {'phase': 'process'},
    }
    second = {
        'run_id': 1,
        'checkpoint_namespace': 'default',
        'checkpoint_id': 'checkpoint-c',
        'parent_checkpoint_id': 'checkpoint-a',
        'body': b'c',
        'serializer_name': 'langgraph-json',
        'serializer_version': 1,
        'content_type': 'application/vnd.langgraph.checkpoint+json',
        'metadata': {'phase': 'process'},
    }
    proc_a = ctx.Process(target=_process_worker, args=(str(root), start, first, queue))
    proc_b = ctx.Process(target=_process_worker, args=(str(root), start, second, queue))
    proc_a.start()
    proc_b.start()
    start.set()
    try:
        proc_a.join(20)
        proc_b.join(20)
        assert not proc_a.is_alive()
        assert not proc_b.is_alive()
        results = [queue.get(timeout=5), queue.get(timeout=5)]
    finally:
        queue.close()
        queue.join_thread()

    assert {result['status'] for result in results} == {'ok', 'error'}
    assert sum(1 for result in results if result['status'] == 'ok') == 1
    assert sum(1 for result in results if result['status'] == 'error' and result['type'] == 'CheckpointConflictError') == 1
    assert _revisions(FilesystemCheckpointStore(root)) == [1, 2]


@pytest.mark.skipif(os.name != 'posix', reason='POSIX advisory locking required')
def test_filesystem_checkpoint_store_process_lock_releases_after_crash(tmp_path: Path) -> None:
    root = tmp_path / 'checkpoint-store'
    ctx = multiprocessing.get_context('spawn')
    locked = ctx.Event()
    proc = ctx.Process(target=_process_lock_worker, args=(str(root), locked))
    proc.start()
    try:
        assert locked.wait(timeout=20)
        proc.join(20)
        assert not proc.is_alive()
    finally:
        if proc.is_alive():  # pragma: no cover - defensive cleanup
            proc.terminate()
            proc.join(5)

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(FilesystemCheckpointStore(root).save, _request(checkpoint_id='checkpoint-a', body=b'a'))
        written = future.result(timeout=20)

    assert written.revision == 1


def test_filesystem_checkpoint_store_after_save_retry_is_idempotent(tmp_path: Path) -> None:
    root = tmp_path / 'checkpoint-store'
    inner = FilesystemCheckpointStore(root)
    wrapped = FaultingCheckpointStore(
        inner,
        plan=FaultPlan(
            operation='save',
            timing=FaultTiming.AFTER,
            occurrence=1,
            exception_factory=lambda: RuntimeError('fault after save'),
        ),
    )
    request = _request(
        checkpoint_id='checkpoint-a',
        body=b'secret-body',
        metadata={'token': 'secret-value', 'nested': {'value': 'keep-me'}},
    )

    with pytest.raises(RuntimeError):
        wrapped.save(request)

    retry = inner.save(request)
    latest = inner.load_latest(1, checkpoint_namespace='default')

    assert retry.revision == 1
    assert latest is not None
    assert latest.checkpoint == retry
    assert latest.body == b'secret-body'
    assert latest.checkpoint.metadata['token'] == 'secret-value'
    assert latest.checkpoint.metadata['nested']['value'] == 'keep-me'
    assert inner.save(request) == retry


def test_filesystem_checkpoint_store_same_size_body_mutation_is_list_safe_but_read_unsafe(tmp_path: Path) -> None:
    root = tmp_path / 'checkpoint-store'
    store = FilesystemCheckpointStore(root)
    store.save(_request(checkpoint_id='checkpoint-a', body=b'a'))
    written = store.save(_request(checkpoint_id='checkpoint-b', parent_checkpoint_id='checkpoint-a', body=b'body-b'))

    body_path = store._body_path(written.digest)
    body_path.write_bytes(b'X' * len(b'body-b'))

    listed = store.list_for_run(1, checkpoint_namespace='default')

    assert [checkpoint.revision for checkpoint in listed] == [1, 2]

    with pytest.raises(CheckpointIntegrityError):
        store.load_checkpoint(1, 'checkpoint-b', checkpoint_namespace='default')

    with pytest.raises(CheckpointIntegrityError):
        store.load_latest(1, checkpoint_namespace='default')


def test_filesystem_checkpoint_store_list_does_not_full_read_body(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / 'checkpoint-store'
    store = FilesystemCheckpointStore(root)
    store.save(_request(checkpoint_id='checkpoint-a', body=b'a'))
    store.save(_request(checkpoint_id='checkpoint-b', parent_checkpoint_id='checkpoint-a', body=b'b'))

    def fail_if_called(*args: object, **kwargs: object) -> None:
        raise AssertionError('list_for_run() must not full-read checkpoint bodies')

    monkeypatch.setattr(FilesystemCheckpointStore, '_verify_record_body', fail_if_called)
    listed = store.list_for_run(1, checkpoint_namespace='default')
    assert [checkpoint.revision for checkpoint in listed] == [1, 2]


def test_filesystem_checkpoint_store_detects_finalized_orphan_record_in_listing(tmp_path: Path) -> None:
    root = tmp_path / 'checkpoint-store'
    store = FilesystemCheckpointStore(root)
    store.save(_request(checkpoint_id='checkpoint-a', body=b'a'))
    store.save(_request(checkpoint_id='checkpoint-b', parent_checkpoint_id='checkpoint-a', body=b'b'))

    stream_key = store._stream_key(1, 'default')
    committed = store._load_record_by_revision(stream_key, 2, verify_body=False)
    assert committed is not None
    orphan = StoredCheckpoint(
        run_id=committed.run_id,
        checkpoint_namespace=committed.checkpoint_namespace,
        checkpoint_id='checkpoint-orphan',
        parent_checkpoint_id=committed.checkpoint_id,
        revision=3,
        serializer_name=committed.serializer_name,
        serializer_version=committed.serializer_version,
        content_type=committed.content_type,
        size=committed.size,
        digest=committed.digest,
        metadata=dict(committed.metadata),
    )
    orphan_path = store._by_id_path(stream_key, orphan.checkpoint_id)
    orphan_path.parent.mkdir(parents=True, exist_ok=True)
    orphan_path.write_bytes(filesystem_store._json_bytes(filesystem_store._safe_record_payload(orphan)))

    with pytest.raises(CheckpointIntegrityError):
        store.list_for_run(1, checkpoint_namespace='default')


@pytest.mark.parametrize(
    ('mutate', 'operation'),
    (
        ('body_missing', 'load'),
        ('body_truncated', 'load'),
        ('body_same_size_mutation', 'load'),
        ('record_malformed', 'load'),
        ('record_duplicate_key', 'load'),
        ('head_malformed', 'load'),
        ('pending_malformed', 'load'),
        ('record_index_mismatch', 'load'),
    ),
)
def test_filesystem_checkpoint_store_integrity_matrix(tmp_path: Path, mutate: str, operation: str) -> None:
    root = tmp_path / 'checkpoint-store'
    store = FilesystemCheckpointStore(root)
    written = store.save(_request(checkpoint_id='checkpoint-a', body=b'checkpoint-body', metadata={'phase': 'run'}))
    store.save(_request(checkpoint_id='checkpoint-b', parent_checkpoint_id='checkpoint-a', body=b'checkpoint-body-2', metadata={'phase': 'run'}))

    body_path = store._body_path(written.digest)
    record_path = store._by_id_path(store._stream_key(1, 'default'), written.checkpoint_id)
    revision_path = store._by_revision_path(store._stream_key(1, 'default'), written.revision)
    head_path = store._head_path(store._stream_key(1, 'default'))
    pending_path = store._pending_path(store._stream_key(1, 'default'))
    sibling = tmp_path / 'sibling.txt'
    sibling.write_text('sibling')

    if mutate == 'body_missing':
        body_path.unlink()
    elif mutate == 'body_truncated':
        body_path.write_bytes(b'checkpoint')
    elif mutate == 'body_same_size_mutation':
        body_path.write_bytes(b'X' * len(b'checkpoint-body'))
    elif mutate == 'record_malformed':
        record_path.write_text('{not-json')
    elif mutate == 'record_duplicate_key':
        record_path.write_text('{"schema_version":1,"schema_version":1}')
    elif mutate == 'head_malformed':
        head_path.write_text('{not-json')
    elif mutate == 'pending_malformed':
        pending_path.write_text('{not-json')
    elif mutate == 'record_index_mismatch':
        wrong_revision_path = store._by_revision_path(store._stream_key(1, 'default'), 2)
        revision_path.write_bytes(wrong_revision_path.read_bytes())
    else:  # pragma: no cover - guard
        raise AssertionError(mutate)

    if operation == 'load':
        with pytest.raises(CheckpointIntegrityError):
            store.load_latest(1, checkpoint_namespace='default')
