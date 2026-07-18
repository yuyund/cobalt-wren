"""Deterministic fault-injection harness tests for persistence stores."""

from __future__ import annotations

import pytest

from langgraph_automation.integrations.artifact.base import ArtifactWriteRequest
from langgraph_automation.integrations.artifact.memory_store import MemoryArtifactStore
from langgraph_automation.integrations.checkpoint.base import CheckpointWriteRequest
from langgraph_automation.integrations.checkpoint.memory_store import MemoryCheckpointStore
from tests.support.persistence import FaultPlan, FaultTiming, FaultingArtifactStore, FaultingCheckpointStore


def test_faulting_artifact_store_before_fault_skips_delegate() -> None:
    inner = MemoryArtifactStore()
    store = FaultingArtifactStore(
        inner,
        plan=FaultPlan(operation='put', timing=FaultTiming.BEFORE, occurrence=1, exception_factory=lambda: RuntimeError('boom')),
    )

    with pytest.raises(RuntimeError, match='boom'):
        store.put(ArtifactWriteRequest(run_id=1, storage_key='run-1/report.md', body=b'report', name='report', kind='text'))

    assert inner.get('run-1/report.md') is None
    assert store.records[-1].delegate_ran is False
    assert store.records[-1].call_count == 1


def test_faulting_artifact_store_after_fault_runs_delegate_then_raises() -> None:
    inner = MemoryArtifactStore()
    store = FaultingArtifactStore(
        inner,
        plan=FaultPlan(operation='put', timing=FaultTiming.AFTER, occurrence=1, exception_factory=lambda: RuntimeError('boom')),
    )

    with pytest.raises(RuntimeError, match='boom'):
        store.put(ArtifactWriteRequest(run_id=2, storage_key='run-2/report.md', body=b'report', name='report', kind='text'))

    assert inner.get('run-2/report.md') is not None
    assert store.records[-1].delegate_ran is True
    assert store.records[-1].call_count == 1


def test_faulting_artifact_store_only_faults_on_nth_call() -> None:
    inner = MemoryArtifactStore()
    store = FaultingArtifactStore(
        inner,
        plan=FaultPlan(operation='put', timing=FaultTiming.BEFORE, occurrence=2, exception_factory=lambda: RuntimeError('boom')),
    )

    store.put(ArtifactWriteRequest(run_id=3, storage_key='run-3/first.md', body=b'first', name='first', kind='text'))
    with pytest.raises(RuntimeError, match='boom'):
        store.put(ArtifactWriteRequest(run_id=3, storage_key='run-3/second.md', body=b'second', name='second', kind='text'))

    assert inner.get('run-3/first.md') is not None
    assert inner.get('run-3/second.md') is None
    assert [record.call_count for record in store.records] == [1, 2]


def test_faulting_checkpoint_store_after_fault_runs_delegate_then_raises() -> None:
    inner = MemoryCheckpointStore()
    store = FaultingCheckpointStore(
        inner,
        plan=FaultPlan(operation='save', timing=FaultTiming.AFTER, occurrence=1, exception_factory=lambda: RuntimeError('boom')),
    )

    request = CheckpointWriteRequest(
        run_id=7,
        checkpoint_namespace='default',
        checkpoint_id='checkpoint-a',
        parent_checkpoint_id=None,
        body=b'checkpoint-body',
        serializer_name='langgraph-json',
        serializer_version=1,
        content_type='application/vnd.langgraph.checkpoint+json',
        metadata={'value': 'secret-token', 'path': '/tmp/secret.txt'},
    )

    with pytest.raises(RuntimeError, match='boom'):
        store.save(request)

    assert inner.load_latest(7, checkpoint_namespace='default').body == b'checkpoint-body'
    assert store.records[-1].delegate_ran is True
    assert store.records[-1].call_count == 1


def test_faulting_checkpoint_store_before_fault_skips_delegate_and_keeps_diagnostics_safe() -> None:
    inner = MemoryCheckpointStore()
    store = FaultingCheckpointStore(
        inner,
        plan=FaultPlan(operation='load_latest', timing=FaultTiming.BEFORE, occurrence=1, exception_factory=lambda: RuntimeError('boom')),
    )

    with pytest.raises(RuntimeError, match='boom'):
        store.load_latest(42)

    record = store.records[-1]
    assert record.delegate_ran is False
    assert record.call_count == 1
    assert 'secret' not in record.safe_identifier.lower()
    assert 'token' not in record.safe_identifier.lower()
    assert '/tmp' not in record.safe_identifier


def test_faulting_wrappers_delegate_normal_operations() -> None:
    artifact_store = FaultingArtifactStore(MemoryArtifactStore())
    checkpoint_store = FaultingCheckpointStore(MemoryCheckpointStore())

    artifact_store.put(ArtifactWriteRequest(run_id=4, storage_key='run-4/report.md', body=b'report', name='report', kind='text', metadata={'run_id': 4}))
    assert artifact_store.get('run-4/report.md') is not None
    assert artifact_store.list_for_run(4) != []

    checkpoint_store.save(
        CheckpointWriteRequest(
            run_id=4,
            checkpoint_namespace='default',
            checkpoint_id='checkpoint-a',
            parent_checkpoint_id=None,
            body=b'ok',
            serializer_name='langgraph-json',
            serializer_version=1,
            content_type='application/vnd.langgraph.checkpoint+json',
            metadata={'value': 'ok'},
        )
    )
    assert checkpoint_store.load_latest(4, checkpoint_namespace='default') is not None
    assert checkpoint_store.load_checkpoint(4, 'checkpoint-a', checkpoint_namespace='default') is not None
    assert checkpoint_store.list_for_run(4, checkpoint_namespace='default') != []
