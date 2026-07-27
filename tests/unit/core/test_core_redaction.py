"""Core redaction helper tests."""

from __future__ import annotations

from copy import deepcopy

from cobalt_wren.core.redaction import REDACTED_VALUE, TRUNCATED_VALUE, redact_mapping, redact_text, redact_value


def test_redact_text_handles_bearer_and_key_value_patterns() -> None:
    text = 'Authorization: Bearer abcdefghijklmnopqrstuvwxyz token=abc123 api_key=secret'

    redacted = redact_text(text)

    assert 'abcdefghijklmnopqrstuvwxyz' not in redacted
    assert 'abc123' not in redacted
    assert 'secret' not in redacted
    assert REDACTED_VALUE in redacted


def test_redact_value_handles_nested_structures_and_case_insensitive_keys() -> None:
    original = {
        'token': 'abc123',
        'API_KEY': 'def456',
        'nested': {
            'password': 'p@ss',
            'keep': ['ok', {'Authorization': 'Bearer super-secret'}],
        },
        'path': '/tmp/private.txt',
        'regular': 'visible',
    }
    snapshot = deepcopy(original)

    redacted = redact_value(original)

    assert redacted['token'] == REDACTED_VALUE
    assert redacted['API_KEY'] == REDACTED_VALUE
    assert redacted['nested']['password'] == REDACTED_VALUE
    assert redacted['nested']['keep'][1]['Authorization'] == REDACTED_VALUE
    assert redacted['path'] == REDACTED_VALUE
    assert redacted['regular'] == 'visible'
    assert original == snapshot


def test_redact_mapping_respects_max_depth() -> None:
    original = {'level1': {'level2': {'level3': {'level4': 'value'}}}}

    redacted = redact_mapping(original, max_depth=1)

    assert redacted['level1'] == {'level2': TRUNCATED_VALUE}
    assert original == {'level1': {'level2': {'level3': {'level4': 'value'}}}}


def test_redact_text_hides_absolute_paths() -> None:
    text = 'error at /tmp/private/output.txt and C:/Users/me/output.txt'

    redacted = redact_text(text)

    assert '/tmp/private/output.txt' not in redacted
    assert 'C:/Users/me/output.txt' not in redacted
    assert REDACTED_VALUE in redacted
