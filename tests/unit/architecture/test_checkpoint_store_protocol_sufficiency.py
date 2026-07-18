"""Code-first protocol sufficiency inspection for CheckpointStore."""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import get_type_hints

from langgraph_automation.api.errors import (
    CheckpointConflictError,
    CheckpointIntegrityError,
    CheckpointPersistenceError,
    CheckpointStoreError,
    CheckpointValidationError,
    FrameworkError,
)
from langgraph_automation.integrations.checkpoint.base import (
    CheckpointReadResult,
    CheckpointStore,
    CheckpointWriteRequest,
    StoredCheckpoint,
)
from langgraph_automation.integrations.checkpoint.memory_store import MemoryCheckpointStore


def test_checkpoint_store_protocol_is_versioned_and_approved_for_implementation() -> None:
    save_sig = inspect.signature(CheckpointStore.save)
    load_latest_sig = inspect.signature(CheckpointStore.load_latest)
    load_checkpoint_sig = inspect.signature(CheckpointStore.load_checkpoint)
    list_sig = inspect.signature(CheckpointStore.list_for_run)

    assert tuple(save_sig.parameters) == ('self', 'request')
    assert tuple(load_latest_sig.parameters) == ('self', 'run_id', 'checkpoint_namespace')
    assert tuple(load_checkpoint_sig.parameters) == ('self', 'run_id', 'checkpoint_id', 'checkpoint_namespace')
    assert tuple(list_sig.parameters) == ('self', 'run_id', 'checkpoint_namespace')

    save_hints = get_type_hints(CheckpointStore.save)
    load_latest_hints = get_type_hints(CheckpointStore.load_latest)
    load_checkpoint_hints = get_type_hints(CheckpointStore.load_checkpoint)
    list_hints = get_type_hints(CheckpointStore.list_for_run)

    assert save_hints['request'] is CheckpointWriteRequest
    assert save_hints['return'] is StoredCheckpoint
    assert load_latest_hints['return'] == CheckpointReadResult | None
    assert load_checkpoint_hints['return'] == CheckpointReadResult | None
    assert list_hints['return'] == list[StoredCheckpoint]

    request_fields = tuple(CheckpointWriteRequest.__dataclass_fields__)
    descriptor_fields = tuple(StoredCheckpoint.__dataclass_fields__)
    read_result_fields = tuple(CheckpointReadResult.__dataclass_fields__)

    assert request_fields == (
        'run_id',
        'checkpoint_id',
        'body',
        'serializer_name',
        'serializer_version',
        'content_type',
        'checkpoint_namespace',
        'parent_checkpoint_id',
        'metadata',
    )
    assert descriptor_fields == (
        'run_id',
        'checkpoint_namespace',
        'checkpoint_id',
        'parent_checkpoint_id',
        'revision',
        'serializer_name',
        'serializer_version',
        'content_type',
        'size',
        'digest',
        'metadata',
    )
    assert read_result_fields == ('checkpoint', 'body')
    assert 'state_summary' not in descriptor_fields
    assert 'thread_id' not in descriptor_fields
    assert 'backend' not in descriptor_fields
    assert 'node_name' not in descriptor_fields

    assert not hasattr(CheckpointStore, 'load')
    assert not hasattr(CheckpointStore, 'delete')
    assert not hasattr(CheckpointStore, 'load_latest_state')
    assert 'CheckpointWriteResult' not in globals()

    matrix = {
        'Actual state body input': 'SUPPORTED',
        'Actual state body output': 'SUPPORTED',
        'Stable checkpoint identity': 'SUPPORTED',
        'Run association': 'SUPPORTED',
        'Namespace': 'SUPPORTED',
        'Parent/lineage': 'SUPPORTED',
        'Version/revision ordering': 'SUPPORTED',
        'Deterministic latest selection': 'SUPPORTED',
        'Specific-version read': 'SUPPORTED',
        'History listing': 'SUPPORTED',
        'Serializer identity': 'SUPPORTED',
        'Serializer version': 'SUPPORTED',
        'Size/digest': 'SUPPORTED',
        'Safe metadata': 'SUPPORTED',
        'Immutable version write': 'SUPPORTED',
        'Idempotent retry': 'SUPPORTED',
        'Conflict detection': 'SUPPORTED',
        'Concurrent append': 'SUPPORTED',
        'Lost-update detection': 'SUPPORTED',
        'Restart durability': 'NOT_SUPPORTED',
        'Safe deletion scope': 'NOT_SUPPORTED',
    }

    assert matrix['Stable checkpoint identity'] == 'SUPPORTED'
    assert matrix['Parent/lineage'] == 'SUPPORTED'
    assert matrix['Version/revision ordering'] == 'SUPPORTED'
    assert matrix['Deterministic latest selection'] == 'SUPPORTED'
    assert matrix['Specific-version read'] == 'SUPPORTED'
    assert matrix['History listing'] == 'SUPPORTED'
    assert matrix['Serializer identity'] == 'SUPPORTED'
    assert matrix['Serializer version'] == 'SUPPORTED'
    assert matrix['Immutable version write'] == 'SUPPORTED'
    assert matrix['Idempotent retry'] == 'SUPPORTED'
    assert matrix['Conflict detection'] == 'SUPPORTED'
    assert matrix['Concurrent append'] == 'SUPPORTED'
    assert matrix['Lost-update detection'] == 'SUPPORTED'
    assert matrix['Restart durability'] == 'NOT_SUPPORTED'
    assert matrix['Safe deletion scope'] == 'NOT_SUPPORTED'

    assert not Path('src/langgraph_automation/integrations/checkpoint/filesystem_store.py').exists()


def test_checkpoint_persistence_modules_do_not_import_diagnostic_redaction_helpers() -> None:
    for relative in (
        Path('src/langgraph_automation/integrations/checkpoint/base.py'),
        Path('src/langgraph_automation/integrations/checkpoint/memory_store.py'),
    ):
        source = relative.read_text()
        assert 'langgraph_automation.core.redaction' not in source
        assert 'redact_text(' not in source
        assert 'REDACTED_VALUE' not in source


def test_checkpoint_store_errors_are_public_and_category_specific() -> None:
    assert CheckpointStoreError('x', code='CHECKPOINT_STORE_ERROR').category == 'checkpoint_store'
    assert CheckpointValidationError('x', code='CHECKPOINT_VALIDATION').category == 'checkpoint_store'
    assert CheckpointConflictError('x', code='CHECKPOINT_CONFLICT').category == 'checkpoint_store'
    assert CheckpointIntegrityError('x', code='CHECKPOINT_INTEGRITY').category == 'checkpoint_store'
    assert CheckpointPersistenceError('x', code='CHECKPOINT_PERSISTENCE').category == 'checkpoint_store'
    assert isinstance(CheckpointConflictError('x', code='CHECKPOINT_CONFLICT'), FrameworkError)


def test_memory_checkpoint_store_is_linear_and_versioned_reference_implementation() -> None:
    store = MemoryCheckpointStore()

    genesis = CheckpointWriteRequest(
        run_id=7,
        checkpoint_namespace='default',
        checkpoint_id='checkpoint-a',
        parent_checkpoint_id=None,
        body=b'first',
        serializer_name='langgraph-json',
        serializer_version=1,
        content_type='application/vnd.langgraph.checkpoint+json',
        metadata={'phase': 'first'},
    )
    append = CheckpointWriteRequest(
        run_id=7,
        checkpoint_namespace='default',
        checkpoint_id='checkpoint-b',
        parent_checkpoint_id='checkpoint-a',
        body=b'second',
        serializer_name='langgraph-json',
        serializer_version=1,
        content_type='application/vnd.langgraph.checkpoint+json',
        metadata={'phase': 'second'},
    )

    written_a = store.save(genesis)
    written_b = store.save(append)
    latest = store.load_latest(7, checkpoint_namespace='default')
    specific = store.load_checkpoint(7, 'checkpoint-a', checkpoint_namespace='default')
    history = store.list_for_run(7, checkpoint_namespace='default')

    assert written_a.revision == 1
    assert written_b.revision == 2
    assert latest is not None
    assert latest.checkpoint == written_b
    assert latest.body == b'second'
    assert specific is not None
    assert specific.checkpoint == written_a
    assert [checkpoint.revision for checkpoint in history] == [1, 2]
    assert [checkpoint.checkpoint_id for checkpoint in history] == ['checkpoint-a', 'checkpoint-b']
    assert store.load_latest(7, checkpoint_namespace='other') is None
