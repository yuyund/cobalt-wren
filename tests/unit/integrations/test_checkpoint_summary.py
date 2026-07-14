'''Checkpoint summary safety tests.'''

from __future__ import annotations

import json

from langgraph_automation.core.redaction import REDACTED_VALUE
from langgraph_automation.integrations.checkpoint import MemoryCheckpointStore, summarize_state


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


def test_memory_checkpoint_store_uses_summarized_state() -> None:
    state = {
        'secret_token': 'abc123',
        'current_step': 'planner' * 20,
    }

    store = MemoryCheckpointStore()
    result = store.save(7, state, thread_id='thread-1', node_name='planner')

    assert 'abc123' not in result.state_summary
    assert 'secret_token' not in result.state_summary
    assert result.state_summary.endswith('}')
    assert len(result.state_summary) < 500
    loaded = json.loads(result.state_summary)
    assert loaded['preview']['***REDACTED***'] == REDACTED_VALUE
