"""Filesystem artifact store contract coverage."""

from __future__ import annotations

import hashlib
import json
import multiprocessing
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from langgraph_automation.api.errors import ArtifactConflictError, ArtifactIntegrityError, ArtifactPersistenceError
from langgraph_automation.integrations.artifact.base import ArtifactReadResult, ArtifactWriteRequest
from langgraph_automation.integrations.artifact.filesystem_store import FilesystemArtifactStore


def _request(
    storage_key: str = 'run-1/report.md',
    *,
    run_id: int | str = 1,
    body: bytes = b'hello world',
    name: str = 'report',
    kind: str = 'text',
    content_type: str | None = 'text/markdown',
    metadata: dict[str, object] | None = None,
) -> ArtifactWriteRequest:
    return ArtifactWriteRequest(
        run_id=run_id,
        storage_key=storage_key,
        body=body,
        name=name,
        kind=kind,
        content_type=content_type,
        metadata=metadata or {},
    )


def _storage_key_digest(storage_key: str) -> str:
    return hashlib.sha256(storage_key.encode('utf-8')).hexdigest()


def _body_digest(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _manifest_path(root: Path, storage_key: str) -> Path:
    digest = _storage_key_digest(storage_key)
    return root / 'records' / 'sha256' / digest[:2] / digest[2:4] / f'{digest}.json'


def _body_path(root: Path, body: bytes) -> Path:
    digest = _body_digest(body)
    return root / 'bodies' / 'sha256' / digest[:2] / digest[2:4] / f'{digest}.blob'


def _write_worker(root: str, request_kwargs: dict[str, object], queue: multiprocessing.Queue) -> None:
    try:
        store = FilesystemArtifactStore(root)
        result = store.put(ArtifactWriteRequest(**request_kwargs))
    except Exception as exc:  # pragma: no cover - exercised in child process
        queue.put({'status': 'error', 'type': exc.__class__.__name__, 'message': str(exc)})
    else:  # pragma: no branch - exercised in child process
        queue.put({'status': 'ok', 'storage_key': result.storage_key, 'digest': result.digest, 'size': result.size})


def _run_process_pair(root: Path, first: dict[str, object], second: dict[str, object]) -> tuple[dict[str, object], dict[str, object]]:
    ctx = multiprocessing.get_context('spawn')
    queue: multiprocessing.Queue = ctx.Queue()
    proc_a = ctx.Process(target=_write_worker, args=(str(root), first, queue))
    proc_b = ctx.Process(target=_write_worker, args=(str(root), second, queue))
    proc_a.start()
    proc_b.start()
    try:
        proc_a.join(20)
        proc_b.join(20)
        if proc_a.is_alive() or proc_b.is_alive():
            proc_a.terminate()
            proc_b.terminate()
            proc_a.join(5)
            proc_b.join(5)
            raise AssertionError('filesystem artifact store process test timed out')
        results = [queue.get(timeout=5), queue.get(timeout=5)]
        if proc_a.exitcode not in (0, None) or proc_b.exitcode not in (0, None):
            raise AssertionError(f'child exit codes were {proc_a.exitcode}, {proc_b.exitcode}')
        return results[0], results[1]
    finally:
        queue.close()
        queue.join_thread()


def test_filesystem_artifact_store_round_trip_and_restart(tmp_path: Path) -> None:
    root = tmp_path / 'artifact-store'
    store_a = FilesystemArtifactStore(root)
    request = _request(metadata={'phase': 'run', 'nested': {'value': 'keep-me'}})

    written = store_a.put(request)
    store_b = FilesystemArtifactStore(root)
    fetched = store_b.get(request.storage_key)

    assert fetched is not None
    assert isinstance(fetched, ArtifactReadResult)
    assert fetched.artifact == written
    assert fetched.body == request.body
    assert [artifact.storage_key for artifact in store_b.list_for_run(request.run_id)] == [request.storage_key]
    assert str(root) not in repr(store_b)


def test_filesystem_artifact_store_same_request_retry_is_idempotent(tmp_path: Path) -> None:
    root = tmp_path / 'artifact-store'
    store = FilesystemArtifactStore(root)
    request = _request(metadata={'phase': 'run', 'nested': {'value': 'keep-me'}})

    first = store.put(request)
    second = store.put(
        _request(
            metadata={'nested': {'value': 'keep-me'}, 'phase': 'run'},
        )
    )

    assert second == first
    assert store.get(request.storage_key).artifact == first


def test_filesystem_artifact_store_conflict_preserves_existing_artifact(tmp_path: Path) -> None:
    root = tmp_path / 'artifact-store'
    store = FilesystemArtifactStore(root)
    request = _request(body=b'hello world', metadata={'phase': 'run'})
    written = store.put(request)

    with pytest.raises(ArtifactConflictError):
        store.put(_request(body=b'goodbye world', metadata={'phase': 'run'}))

    fetched = store.get(request.storage_key)
    assert fetched is not None
    assert fetched.artifact == written
    assert fetched.body == request.body


def test_filesystem_artifact_store_thread_concurrency_same_request(tmp_path: Path) -> None:
    root = tmp_path / 'artifact-store'
    request = _request(storage_key='run-1/thread.md', metadata={'phase': 'thread'})
    barrier = threading.Barrier(2)

    def worker() -> tuple[str, str]:
        store = FilesystemArtifactStore(root)
        barrier.wait(timeout=5)
        written = store.put(request)
        return written.storage_key, written.digest

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: worker(), (None, None)))

    assert results[0] == results[1]
    fetched = FilesystemArtifactStore(root).get(request.storage_key)
    assert fetched is not None
    assert fetched.artifact.digest == results[0][1]


def test_filesystem_artifact_store_thread_concurrency_conflict(tmp_path: Path) -> None:
    root = tmp_path / 'artifact-store'
    barrier = threading.Barrier(2)
    requests = (
        _request(storage_key='run-1/thread-conflict.md', body=b'body-a', metadata={'phase': 'thread'}),
        _request(storage_key='run-1/thread-conflict.md', body=b'body-b', metadata={'phase': 'thread'}),
    )

    results: list[tuple[str, str]] = []
    errors: list[str] = []

    def worker(request: ArtifactWriteRequest) -> None:
        store = FilesystemArtifactStore(root)
        barrier.wait(timeout=5)
        try:
            written = store.put(request)
        except ArtifactConflictError as exc:
            errors.append(str(exc))
        else:
            results.append((written.storage_key, written.digest))

    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(worker, requests))

    assert len(results) == 1
    assert len(errors) == 1
    fetched = FilesystemArtifactStore(root).get(requests[0].storage_key)
    assert fetched is not None
    assert fetched.artifact.digest == results[0][1]


def test_filesystem_artifact_store_process_concurrency_same_request(tmp_path: Path) -> None:
    root = tmp_path / 'artifact-store'
    request_kwargs = {
        'run_id': 1,
        'storage_key': 'run-1/process.md',
        'body': b'process body',
        'name': 'report',
        'kind': 'text',
        'content_type': 'text/markdown',
        'metadata': {'phase': 'process'},
    }

    first, second = _run_process_pair(root, request_kwargs, request_kwargs)
    assert first['status'] == 'ok'
    assert second['status'] == 'ok'
    assert first['digest'] == second['digest']
    fetched = FilesystemArtifactStore(root).get(request_kwargs['storage_key'])
    assert fetched is not None
    assert fetched.artifact.digest == first['digest']


def test_filesystem_artifact_store_process_concurrency_conflict(tmp_path: Path) -> None:
    root = tmp_path / 'artifact-store'
    first_request = {
        'run_id': 1,
        'storage_key': 'run-1/process-conflict.md',
        'body': b'process-a',
        'name': 'report',
        'kind': 'text',
        'content_type': 'text/markdown',
        'metadata': {'phase': 'process'},
    }
    second_request = {
        'run_id': 1,
        'storage_key': 'run-1/process-conflict.md',
        'body': b'process-b',
        'name': 'report',
        'kind': 'text',
        'content_type': 'text/markdown',
        'metadata': {'phase': 'process'},
    }

    first, second = _run_process_pair(root, first_request, second_request)
    assert {first['status'], second['status']} == {'ok', 'error'}
    error = first if first['status'] == 'error' else second
    assert error['type'] == 'ArtifactConflictError'
    fetched = FilesystemArtifactStore(root).get(first_request['storage_key'])
    assert fetched is not None
    assert fetched.body in {first_request['body'], second_request['body']}


def test_filesystem_artifact_store_manifest_is_deterministic_and_bodyless(tmp_path: Path) -> None:
    root = tmp_path / 'artifact-store'
    store = FilesystemArtifactStore(root)
    request = _request(
        storage_key='run-1/manifest.md',
        body=b'manifest body',
        metadata={'nested': {'value': 'keep-me'}, 'phase': 'run'},
    )

    first = store.put(request)
    manifest_path = _manifest_path(root, request.storage_key)
    manifest_bytes = manifest_path.read_bytes()
    payload = json.loads(manifest_bytes.decode('utf-8'))

    assert payload['schema_version'] == 1
    assert 'body' not in manifest_bytes.decode('utf-8')
    assert str(root) not in manifest_bytes.decode('utf-8')
    assert payload['storage_key'] == request.storage_key
    assert payload['digest'] == first.digest
    assert payload['size'] == first.size

    second = store.put(_request(storage_key='run-1/manifest.md', body=b'manifest body', metadata={'phase': 'run', 'nested': {'value': 'keep-me'}}))
    assert second == first
    assert manifest_bytes == manifest_path.read_bytes()


@pytest.mark.parametrize(
    ('mutate', 'expect_get_exception'),
    (
        ('missing_body', True),
        ('truncated_body', True),
        ('same_size_body_mutation', True),
        ('malformed_manifest', True),
        ('duplicate_key_manifest', True),
        ('unsupported_schema', True),
        ('wrong_storage_key', True),
        ('wrong_size', True),
        ('wrong_digest', True),
        ('body_symlink', True),
        ('manifest_symlink', True),
        ('body_directory', True),
        ('manifest_directory', True),
        ('oversized_manifest', True),
    ),
)
def test_filesystem_artifact_store_detects_corruption_matrix(tmp_path: Path, mutate: str, expect_get_exception: bool) -> None:
    root = tmp_path / 'artifact-store'
    store = FilesystemArtifactStore(root)
    request = _request(storage_key='run-1/corrupt.md', body=b'corrupt-body', metadata={'phase': 'run'})
    store.put(request)

    manifest_path = _manifest_path(root, request.storage_key)
    body_path = _body_path(root, request.body)
    sibling = tmp_path / 'sibling.txt'
    sibling.write_text('sibling')

    if mutate == 'missing_body':
        body_path.unlink()
    elif mutate == 'truncated_body':
        body_path.write_bytes(request.body[:-2])
    elif mutate == 'same_size_body_mutation':
        body_path.write_bytes(b'X' * len(request.body))
    elif mutate == 'malformed_manifest':
        manifest_path.write_text('{not-json')
    elif mutate == 'duplicate_key_manifest':
        manifest_path.write_text('{"schema_version":1,"schema_version":1}')
    elif mutate == 'unsupported_schema':
        payload = json.loads(manifest_path.read_text())
        payload['schema_version'] = 2
        manifest_path.write_text(json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False))
    elif mutate == 'wrong_storage_key':
        payload = json.loads(manifest_path.read_text())
        payload['storage_key'] = 'run-1/other.md'
        manifest_path.write_text(json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False))
    elif mutate == 'wrong_size':
        payload = json.loads(manifest_path.read_text())
        payload['size'] = payload['size'] + 1
        payload['digest'] = 'sha256:' + _body_digest(request.body)
        manifest_path.write_text(json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False))
    elif mutate == 'wrong_digest':
        payload = json.loads(manifest_path.read_text())
        payload['digest'] = 'sha256:' + '0' * 64
        manifest_path.write_text(json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False))
    elif mutate == 'body_symlink':
        body_path.unlink()
        body_path.symlink_to(sibling)
    elif mutate == 'manifest_symlink':
        manifest_path.unlink()
        manifest_path.symlink_to(sibling)
    elif mutate == 'body_directory':
        body_path.unlink()
        body_path.mkdir()
    elif mutate == 'manifest_directory':
        manifest_path.unlink()
        manifest_path.mkdir()
    elif mutate == 'oversized_manifest':
        payload = json.loads(manifest_path.read_text())
        payload['metadata'] = {'padding': 'x' * (1024 * 1024)}
        manifest_path.write_text(json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False))
    else:  # pragma: no cover - guard for future additions
        raise AssertionError(mutate)

    with pytest.raises(ArtifactIntegrityError):
        store.get(request.storage_key)


def test_filesystem_artifact_store_list_detects_wrong_filename_mapping(tmp_path: Path) -> None:
    root = tmp_path / 'artifact-store'
    store = FilesystemArtifactStore(root)
    request = _request(storage_key='run-1/list-corrupt.md', body=b'list-body', metadata={'phase': 'run'})
    store.put(request)

    manifest_path = _manifest_path(root, request.storage_key)
    wrong_path = manifest_path.with_name('f' * 64 + '.json')
    wrong_path.write_bytes(manifest_path.read_bytes())
    manifest_path.unlink()

    with pytest.raises(ArtifactIntegrityError):
        store.list_for_run(request.run_id)


def test_filesystem_artifact_store_safe_errors_hide_sensitive_paths(tmp_path: Path) -> None:
    root = tmp_path / 'SUPER_SECRET_ROOT_SENTINEL'
    store = FilesystemArtifactStore(root)
    request = _request(storage_key='run-1/safe.md', body=b'SUPER_SECRET_BODY_SENTINEL', metadata={'token': 'SUPER_SECRET_METADATA_SENTINEL'})
    store.put(request)

    body_path = _body_path(root, request.body)
    body_path.unlink()

    with pytest.raises(ArtifactIntegrityError) as exc_info:
        store.get(request.storage_key)

    text = str(exc_info.value)
    assert 'SUPER_SECRET_ROOT_SENTINEL' not in text
    assert 'SUPER_SECRET_BODY_SENTINEL' not in text
    assert 'SUPER_SECRET_METADATA_SENTINEL' not in text
    assert '/tmp' not in text
    assert repr(store).find('SUPER_SECRET_ROOT_SENTINEL') == -1


def test_filesystem_artifact_store_retries_after_body_then_manifest_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / 'artifact-store'
    store = FilesystemArtifactStore(root)
    request = _request(storage_key='run-1/fault.md', body=b'fault-body', metadata={'phase': 'run'})
    calls: list[str] = []
    original_link = os.link

    def flaky_link(src: str, dst: str, *args: object, **kwargs: object) -> None:
        dst_text = str(dst)
        calls.append(dst_text)
        if dst_text.endswith('.json') and len(calls) == 2:
            raise OSError('unsupported')
        return original_link(src, dst, *args, **kwargs)

    monkeypatch.setattr('langgraph_automation.integrations.artifact.filesystem_store.os.link', flaky_link)
    with pytest.raises(ArtifactPersistenceError):
        store.put(request)

    assert _body_path(root, request.body).exists()
    assert _manifest_path(root, request.storage_key).exists() is False

    monkeypatch.setattr('langgraph_automation.integrations.artifact.filesystem_store.os.link', original_link)
    written = store.put(request)
    fetched = store.get(request.storage_key)
    assert fetched is not None
    assert fetched.artifact == written


def test_filesystem_artifact_store_cleanup_failure_does_not_override_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / 'artifact-store'
    store = FilesystemArtifactStore(root)
    request = _request(storage_key='run-1/cleanup.md', body=b'cleanup-body', metadata={'phase': 'run'})
    original_unlink = os.unlink

    def flaky_unlink(path: str, *args: object, **kwargs: object) -> None:
        if Path(path).name.startswith('.tmp-'):
            raise OSError('cleanup failed')
        return original_unlink(path, *args, **kwargs)

    monkeypatch.setattr('langgraph_automation.integrations.artifact.filesystem_store.os.unlink', flaky_unlink)
    written = store.put(request)
    assert written.storage_key == request.storage_key
    assert store.get(request.storage_key) is not None
