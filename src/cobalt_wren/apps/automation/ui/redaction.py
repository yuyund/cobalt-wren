"""Redaction helpers for sensitive values shown in the dynamic UI."""

from __future__ import annotations

from typing import Any

from cobalt_wren.core.redaction import redact_mapping, redact_value as core_redact_value


def redact_value(name: str, value: object) -> tuple[object, bool]:
    """Redact a field value and report whether the value changed."""

    redacted = core_redact_value(value, key_name=name)
    return redacted, redacted != value


def redact_payload(payload: object) -> object:
    """Redact a payload recursively for UI display."""

    return core_redact_value(payload)


def redact_mapping_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Redact a mapping recursively for UI display."""

    return redact_mapping(payload)
