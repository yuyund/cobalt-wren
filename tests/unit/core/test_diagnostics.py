from cobalt_wren.apps.automation.services.diagnostics import (
    build_bounded_diagnostic,
)


def test_bounded_diagnostic_redacts_secrets_and_preserves_useful_values() -> None:
    result = build_bounded_diagnostic(
        {"operation": "execute", "api_token": "secret-value", "items": list(range(120))}
    )
    assert result.payload["operation"] == "execute"
    assert result.payload["api_token"] == "***REDACTED***"
    assert "secret-value" not in repr(result.payload)
    assert result.truncated is True
    assert result.byte_size <= 64 * 1024


def test_bounded_diagnostic_marks_long_text_as_partial() -> None:
    result = build_bounded_diagnostic({"message": "x" * 3000})
    assert result.truncated is True
    assert result.truncation_reason == "bounded_limit"
    assert str(result.payload["message"]).endswith("…")
