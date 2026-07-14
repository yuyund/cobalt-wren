"""Core summary helper tests."""

from __future__ import annotations

from langgraph_automation.core.redaction import REDACTED_VALUE
from langgraph_automation.core.summary import hash_text, preview_text, summarize_mapping, summarize_messages, summarize_sequence, truncate_text


def test_truncate_text_bounds_length() -> None:
    text = 'x' * 600

    truncated = truncate_text(text, max_chars=50)

    assert len(truncated) <= 50
    assert truncated.endswith('***TRUNCATED***') or truncated == '***TRUNCATED***'


def test_preview_text_is_redacted_and_bounded() -> None:
    text = 'Authorization: Bearer very-long-secret-value ' + ('x' * 200)

    preview = preview_text(text, max_chars=80)

    assert 'very-long-secret-value' not in preview
    assert REDACTED_VALUE in preview
    assert len(preview) <= 80


def test_hash_text_returns_sha256_prefix() -> None:
    hashed = hash_text('hello world')

    assert hashed.startswith('sha256:')
    assert len(hashed) == len('sha256:') + 64


def test_summarize_mapping_bounded_and_redacted() -> None:
    value = {
        'secret': 'abc',
        'nested': {'token': 'def', 'values': [1, 2, 3]},
        'plain': 'visible',
    }

    summary = summarize_mapping(value, max_depth=2)

    assert summary['preview']['***REDACTED***'] == REDACTED_VALUE
    assert summary['preview']['nested']['preview']['***REDACTED***'] == REDACTED_VALUE
    assert summary['preview']['plain'] == 'visible'


def test_summarize_sequence_bounds_items() -> None:
    summary = summarize_sequence(list(range(50)), max_items=5)

    assert summary == [0, 1, 2, 3, 4]


def test_summarize_messages_returns_hash_preview_and_roles() -> None:
    messages = [
        {'role': 'system', 'content': 'hello'},
        {'role': 'user', 'content': 'Authorization: Bearer abcdefghijklmnop'},
        {'role': 'assistant', 'content': 'result'},
    ]

    summary = summarize_messages(messages)

    assert summary['message_count'] == 3
    assert summary['roles'] == ['system', 'user', 'assistant']
    assert summary['prompt_hash'].startswith('sha256:')
    assert 'abcdefghijklmnop' not in summary['preview']
    assert REDACTED_VALUE in summary['preview']
    assert 'abcdefghijklmnop' not in summary['preview']
    assert 'hello' in summary['preview']
    assert 'result' in summary['preview']
