"""Code-first protocol sufficiency inspection for CheckpointStore."""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any, get_type_hints

from langgraph_automation.integrations.checkpoint.base import CheckpointStore, CheckpointWriteResult
from langgraph_automation.integrations.checkpoint.memory_store import MemoryCheckpointStore


def test_checkpoint_store_protocol_is_blocked_by_missing_versioned_contract() -> None:
    save_sig = inspect.signature(CheckpointStore.save)
    load_sig = inspect.signature(CheckpointStore.load)
    delete_sig = inspect.signature(CheckpointStore.delete)

    assert tuple(save_sig.parameters) == (
        'self',
        'run_id',
        'state',
        'thread_id',
        'checkpoint_namespace',
        'backend',
        'node_name',
    )
    assert tuple(load_sig.parameters) == ('self', 'run_id')
    assert tuple(delete_sig.parameters) == ('self', 'run_id')

    save_hints = get_type_hints(CheckpointStore.save)
    load_hints = get_type_hints(CheckpointStore.load)
    delete_hints = get_type_hints(CheckpointStore.delete)

    assert save_hints['run_id'] is int
    assert save_hints['state'] == dict[str, Any]
    assert save_hints['return'] is CheckpointWriteResult
    assert load_hints['return'] == dict[str, Any] | None
    assert delete_hints['return'] is type(None)

    result_fields = tuple(CheckpointWriteResult.__dataclass_fields__)
    assert result_fields == ('checkpoint_id', 'thread_id', 'checkpoint_namespace', 'backend', 'node_name', 'state_summary')
    assert 'serializer' not in result_fields
    assert 'serializer_version' not in result_fields
    assert 'version' not in result_fields
    assert 'revision' not in result_fields
    assert 'parent_checkpoint_id' not in result_fields
    assert 'size' not in result_fields
    assert 'digest' not in result_fields

    matrix = {
        'Actual state body input': 'PARTIALLY_SUPPORTED',
        'Actual state body output': 'PARTIALLY_SUPPORTED',
        'Stable checkpoint identity': 'NOT_SUPPORTED',
        'Run association': 'PARTIALLY_SUPPORTED',
        'Thread identity': 'PARTIALLY_SUPPORTED',
        'Namespace': 'PARTIALLY_SUPPORTED',
        'Parent/lineage': 'NOT_SUPPORTED',
        'Version/revision ordering': 'NOT_SUPPORTED',
        'Deterministic latest selection': 'NOT_SUPPORTED',
        'Specific-version read': 'NOT_SUPPORTED',
        'History listing': 'NOT_SUPPORTED',
        'Serializer identity': 'NOT_SUPPORTED',
        'Serializer version': 'NOT_SUPPORTED',
        'Size/digest': 'NOT_SUPPORTED',
        'Safe metadata': 'PARTIALLY_SUPPORTED',
        'Immutable version write': 'NOT_SUPPORTED',
        'Idempotent retry': 'NOT_SUPPORTED',
        'Conflict detection': 'NOT_SUPPORTED',
        'Concurrent append': 'NOT_SUPPORTED',
        'Lost-update detection': 'NOT_SUPPORTED',
        'Restart durability': 'NOT_SUPPORTED',
        'Safe deletion scope': 'PARTIALLY_SUPPORTED',
    }

    assert matrix['Stable checkpoint identity'] == 'NOT_SUPPORTED'
    assert matrix['Parent/lineage'] == 'NOT_SUPPORTED'
    assert matrix['Version/revision ordering'] == 'NOT_SUPPORTED'
    assert matrix['Deterministic latest selection'] == 'NOT_SUPPORTED'
    assert matrix['Specific-version read'] == 'NOT_SUPPORTED'
    assert matrix['History listing'] == 'NOT_SUPPORTED'
    assert matrix['Serializer identity'] == 'NOT_SUPPORTED'
    assert matrix['Serializer version'] == 'NOT_SUPPORTED'
    assert matrix['Immutable version write'] == 'NOT_SUPPORTED'
    assert matrix['Conflict detection'] == 'NOT_SUPPORTED'
    assert matrix['Concurrent append'] == 'NOT_SUPPORTED'
    assert matrix['Lost-update detection'] == 'NOT_SUPPORTED'
    assert matrix['Restart durability'] == 'NOT_SUPPORTED'
    assert matrix['Safe deletion scope'] == 'PARTIALLY_SUPPORTED'

    assert not Path('src/langgraph_automation/integrations/checkpoint/filesystem_store.py').exists()


def test_memory_checkpoint_store_is_currently_latest_state_replacement() -> None:
    store = MemoryCheckpointStore()

    first = store.save(7, {'phase': 'first'}, thread_id='thread-7', checkpoint_namespace='default', backend='memory', node_name='planner')
    second = store.save(7, {'phase': 'second'}, thread_id='thread-7', checkpoint_namespace='default', backend='memory', node_name='planner')

    assert first.checkpoint_id != second.checkpoint_id
    assert store.load(7) == {'phase': 'second'}
    store.delete(7)
    assert store.load(7) is None
