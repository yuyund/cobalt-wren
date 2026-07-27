from __future__ import annotations
from cobalt_wren.apps.automation.ui.values import (
    build_value_spec,
    parse_summary_value,
)


def test_summary_json_string_is_parsed_but_ordinary_text_is_not() -> None:
    summary = parse_summary_value("input_summary", '{"preview": {"answer": "ok"}}')
    ordinary = parse_summary_value("message", '{"preview": {"answer": "ok"}}')
    assert summary == {"preview": {"answer": "ok"}}
    assert ordinary == '{"preview": {"answer": "ok"}}'


def test_value_spec_projects_nested_values_without_renderer_details() -> None:
    spec = build_value_spec(
        {
            "provider": "fake",
            "usage": {"input_tokens": 4},
            "roles": ["user", "assistant"],
        }
    )
    assert spec.kind == "mapping"
    assert spec.summary == "3 fields"
    assert [entry.key for entry in spec.entries] == ["Provider", "Usage", "Roles"]
    assert spec.entries[1].value.kind == "mapping"
    assert spec.entries[2].value.kind == "list"
    assert "fake" in spec.json_text
    assert "bg-" not in repr(spec)
    assert "template" not in repr(spec)


def test_value_spec_marks_redacted_truncated_and_empty_values() -> None:
    assert build_value_spec("***REDACTED***").kind == "redacted"
    assert build_value_spec("***TRUNCATED***").kind == "truncated"
    assert build_value_spec({}).kind == "mapping"
    assert build_value_spec({}).summary == "0 fields"
    assert build_value_spec(None).kind == "empty"


def test_value_spec_bounds_large_mappings() -> None:
    spec = build_value_spec({f"field_{index}": index for index in range(30)})
    assert spec.count == 30
    assert len(spec.entries) == 20
    assert spec.truncated is True


def test_summary_python_literal_is_parsed_without_executing_code() -> None:
    parsed = parse_summary_value(
        "state_summary", "{'status': 'compensated', 'attempt': 2}"
    )
    unsafe = parse_summary_value(
        "state_summary", "__import__('os').system('echo unsafe')"
    )
    ordinary = parse_summary_value("message", "{'status': 'compensated'}")
    assert parsed == {"status": "compensated", "attempt": 2}
    assert unsafe == "__import__('os').system('echo unsafe')"
    assert ordinary == "{'status': 'compensated'}"


def test_summary_envelope_prefers_preview_and_hides_technical_keys() -> None:
    spec = build_value_spec(
        {
            "keys": ["status"],
            "types": {"status": "str"},
            "sizes": {"status": 11},
            "preview": {"status": "compensated"},
        }
    )
    assert spec.kind == "mapping"
    assert [(entry.key, entry.value.text) for entry in spec.entries] == [
        ("Status", "compensated")
    ]
    assert "keys" in spec.json_text


def test_summary_envelope_without_preview_renders_compact_schema() -> None:
    spec = build_value_spec(
        {
            "value_type": "dict",
            "size": 1,
            "keys": ["status"],
            "types": {"status": "str"},
            "sizes": {"status": 11},
        }
    )
    assert spec.kind == "mapping"
    assert [(entry.key, entry.value.text) for entry in spec.entries] == [
        ("Status", "str · 11 chars")
    ]
    assert all(
        entry.key not in {"Value Type", "Keys", "Types", "Sizes"}
        for entry in spec.entries
    )


def test_value_spec_unwraps_repeated_summary_wrappers() -> None:
    spec = build_value_spec(
        {
            "preview": {
                "input_summary": {"preview": {"preview": "user: Explain this result"}}
            }
        }
    )
    assert spec.kind == "text"
    assert spec.text == "user: Explain this result"


def test_value_spec_parses_structured_json_inside_safe_preview() -> None:
    spec = build_value_spec(
        {
            "keys": ["payload"],
            "types": {"payload": "str"},
            "sizes": {"payload": 18},
            "preview": '{"preview": "completed"}',
        }
    )
    assert spec.kind == "text"
    assert spec.text == "completed"


def test_value_spec_normalizes_nested_summary_envelopes_recursively() -> None:
    spec = build_value_spec(
        {
            "workflow": {
                "keys": ["kind", "config"],
                "types": {"kind": "str", "config": "dict"},
                "sizes": {"kind": 15, "config": 1},
                "preview": {
                    "kind": "plain_python",
                    "config": {
                        "keys": ["timeout"],
                        "types": {"timeout": "int"},
                        "sizes": {},
                        "preview": {"timeout": 30},
                    },
                },
            }
        }
    )
    workflow = spec.entries[0].value
    assert workflow.kind == "mapping"
    assert [entry.key for entry in workflow.entries] == ["Kind", "Config"]
    assert workflow.entries[0].value.text == "plain_python"
    assert [
        (entry.key, entry.value.text) for entry in workflow.entries[1].value.entries
    ] == [("Timeout", "30")]
    assert all(
        entry.key not in {"Keys", "Types", "Sizes", "Preview"}
        for entry in workflow.entries
    )


def test_value_spec_unwraps_value_type_size_summary_envelope() -> None:
    spec = build_value_spec(
        {
            "value_type": "dict",
            "size": 2,
            "summary": {"status": "ready", "count": 4},
        }
    )
    assert [(entry.key, entry.value.text) for entry in spec.entries] == [
        ("Status", "ready"),
        ("Count", "4"),
    ]


def test_value_spec_prefers_message_previews_over_duplicate_input_summary() -> None:
    spec = build_value_spec(
        {
            "input_summary": {"messages": [{"role": "system", "preview": "truncated"}]},
            "message_previews": [{"role": "system", "preview": "Explain the result"}],
            "provider": "demo",
            "model": "test-model",
        }
    )
    assert [entry.key for entry in spec.entries] == [
        "Message Previews",
        "Provider",
        "Model",
    ]
    message = {
        entry.key: entry.value.text for entry in spec.entries[0].value.items[0].entries
    }
    assert message == {"Role": "system", "Preview": "Explain the result"}


def test_truncated_marker_is_preview_unavailable_not_generic_truncated() -> None:
    spec = build_value_spec("***TRUNCATED***")
    assert spec.kind == "truncated"
    assert spec.text == "Preview unavailable"
    assert spec.quality == "unavailable"
    assert not spec.has_meaningful_value


def test_summary_omitted_count_is_preserved_in_value_spec() -> None:
    spec = build_value_spec(
        {
            "keys": ["status"],
            "types": {"status": "str"},
            "sizes": {"status": 5},
            "preview": {"status": "ready"},
            "truncated": True,
            "omitted_count": 4,
            "truncation_reason": "item_limit",
        }
    )
    assert spec.truncated is True
    assert spec.omitted_count == 4
    assert spec.truncation_reason == "item_limit"
    assert spec.quality == "partial"
