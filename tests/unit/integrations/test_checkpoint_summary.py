'''Checkpoint summary safety tests.'''

from __future__ import annotations

import json

from cobalt_wren.core.redaction import REDACTED_VALUE
from cobalt_wren.integrations.checkpoint import CheckpointWriteRequest, MemoryCheckpointStore, summarize_state


def test_summarize_state_redacts_sensitive_keys_and_bounded_values() -> None:
    state = {
        'messages': ['hello', 'world', '!' * 100],
        'secret_token': 'abc123',
        'details': {
            'path': '/tmp/secret/file.txt',
            'name': 'alice',
        },
        'current_step': 'planner' * 20,
    }

    summary = summarize_state(state)

    assert summary['keys'] == ['messages', '***REDACTED***', 'details', 'current_step']
    assert summary['preview']['***REDACTED***'] == REDACTED_VALUE
    assert summary['preview']['details']['keys'] == ['***REDACTED***', 'name']
    assert summary['preview']['details']['preview']['***REDACTED***'] == REDACTED_VALUE
    assert summary['sizes']['messages'] == 3
    assert len(summary['preview']['current_step']) <= 300
    assert summary['preview']['current_step'].startswith('planner')
    assert 'abc123' not in json.dumps(summary)
    assert '/tmp/secret/file.txt' not in json.dumps(summary)


def test_memory_checkpoint_store_versioned_append_and_history() -> None:
    store = MemoryCheckpointStore()

    first = store.save(
        CheckpointWriteRequest(
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
    )
    second = store.save(
        CheckpointWriteRequest(
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
    )

    assert first.revision == 1
    assert second.revision == 2
    latest = store.load_latest(7, checkpoint_namespace='default')
    assert latest is not None
    assert latest.checkpoint == second
    assert latest.body == b'second'
    assert [checkpoint.revision for checkpoint in store.list_for_run(7, checkpoint_namespace='default')] == [1, 2]


def test_memory_checkpoint_store_uses_summarized_state() -> None:
    state = {
        'secret_token': 'abc123',
        'current_step': 'planner' * 20,
    }

    summary = summarize_state(state)

    assert 'abc123' not in json.dumps(summary)
    assert 'secret_token' not in json.dumps(summary)
    assert len(json.dumps(summary)) < 500
    assert summary['preview']['***REDACTED***'] == REDACTED_VALUE
