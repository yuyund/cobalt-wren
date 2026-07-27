'''Redaction tests for dynamic UI payloads.'''

from __future__ import annotations

from cobalt_wren.apps.automation.ui.redaction import redact_payload, redact_value
from cobalt_wren.core.redaction import REDACTED_VALUE


def test_redact_value_hides_sensitive_fields() -> None:
    value, redacted = redact_value('api_key', 'secret-value')

    assert redacted is True
    assert value == REDACTED_VALUE


def test_redact_payload_hides_nested_sensitive_keys() -> None:
    payload = {
        'token': 'abc',
        'nested': {
            'password': 'pw',
            'safe': 'ok',
        },
        'items': [
            {'path': '/tmp/file'},
            {'name': 'visible'},
        ],
    }

    redacted = redact_payload(payload)

    assert redacted['token'] == REDACTED_VALUE
    assert redacted['nested']['password'] == REDACTED_VALUE
    assert redacted['items'][0]['path'] == REDACTED_VALUE
    assert redacted['items'][1]['name'] == 'visible'
