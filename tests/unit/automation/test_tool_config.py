"""Workflow tool config extraction tests."""

from __future__ import annotations

from langgraph_automation.apps.automation.services.tool_config import extract_allowed_tool_names


def test_extract_allowed_tool_names_returns_empty_tuple_for_missing_or_invalid_config() -> None:
    assert extract_allowed_tool_names(None) == ()
    assert extract_allowed_tool_names({}) == ()
    assert extract_allowed_tool_names({'tools': {}}) == ()
    assert extract_allowed_tool_names({'tools': {'allowed': None}}) == ()
    assert extract_allowed_tool_names({'tools': {'allowed': ()}}) == ()
    assert extract_allowed_tool_names({'tools': {'allowed': []}}) == ()
    assert extract_allowed_tool_names({'tools': {'allowed': ''}}) == ()


def test_extract_allowed_tool_names_filters_invalid_entries_and_preserves_order() -> None:
    payload = {
        'tools': {
            'allowed': ['echo', ' ', 'echo', 123, 'shell', 'echo', 'file', 'shell'],
        }
    }

    assert extract_allowed_tool_names(payload) == ('echo', 'shell', 'file')
