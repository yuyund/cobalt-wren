"""Run result safety helper tests."""

from __future__ import annotations

from cobalt_wren.core.redaction import REDACTED_VALUE
from cobalt_wren.core.result_safety import safe_run_error_message, safe_run_output_payload


def test_safe_run_output_payload_redacts_nested_mapping_and_bounds_output() -> None:
    value = {
        'summary': 'done',
        'secret': 'abc123',
        'path': '/tmp/secret.txt',
        'nested': {
            'token': 'def456',
            'items': ['Authorization: Bearer xxxxxxxxxxxxxxxx', {'password': 'swordfish'}],
        },
        'long_text': 'x' * 500,
    }

    safe = safe_run_output_payload(value)

    assert safe['value_type'] == 'dict'
    assert safe['size'] == len(value)
    assert safe['summary']['preview']['summary'] == 'done'
    assert safe['summary']['preview']['secret'] == REDACTED_VALUE
    assert safe['summary']['preview']['path'] == REDACTED_VALUE
    assert safe['summary']['preview']['nested']['preview']['token'] == REDACTED_VALUE
    assert REDACTED_VALUE in safe['summary']['preview']['nested']['preview']['items'][0]
    assert safe['summary']['preview']['nested']['preview']['items'][1]['preview']['password'] == REDACTED_VALUE
    assert 'abc123' not in repr(safe)
    assert '/tmp/secret.txt' not in repr(safe)
    assert 'def456' not in repr(safe)


def test_safe_run_output_payload_bounds_strings() -> None:
    safe = safe_run_output_payload('Authorization: Bearer abcdefghijklmnop /tmp/leak.txt ' + ('x' * 500))

    assert safe['value_type'] == 'str'
    assert len(safe['summary']['preview']) <= 300
    assert REDACTED_VALUE in safe['summary']['preview']
    assert '/tmp/leak.txt' not in safe['summary']['preview']


def test_safe_run_error_message_redacts_and_bounded_exception_message() -> None:
    error = ValueError('Authorization: Bearer secret-token /tmp/secret.txt ' + ('x' * 500))

    message = safe_run_error_message(error)

    assert message.startswith('ValueError: ')
    assert REDACTED_VALUE in message
    assert 'secret-token' not in message
    assert '/tmp/secret.txt' not in message
    assert len(message) <= len('ValueError: ') + 300


def test_safe_run_error_message_handles_string_input() -> None:
    message = safe_run_error_message('token=abc123 password=hunter2')

    assert message.startswith('Error: ')
    assert REDACTED_VALUE in message
    assert 'abc123' not in message
    assert 'hunter2' not in message


def test_safe_run_error_message_discards_traceback_like_multiline_input() -> None:
    message = safe_run_error_message(
        'Traceback (most recent call last):\n'
        '  File "/tmp/secret.txt", line 1, in <module>\n'
        'RuntimeError: Authorization: Bearer secret-token /tmp/secret.txt'
    )

    assert message.startswith('Error: ')
    assert 'Traceback' not in message
    assert 'File "/tmp/secret.txt"' not in message
    assert 'secret-token' not in message
    assert '/tmp/secret.txt' not in message
    assert REDACTED_VALUE in message
