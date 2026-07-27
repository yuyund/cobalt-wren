"""Shared bounded summary helpers for payloads, mappings, and messages."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

from .redaction import (
    REDACTED_VALUE,
    TRUNCATED_VALUE,
    is_sensitive_key,
    redact_mapping,
    redact_text,
)

DEFAULT_TRUNCATE_CHARS = 500
DEFAULT_PREVIEW_CHARS = 300
DEFAULT_MAX_DEPTH = 3
DEFAULT_MAX_ITEMS = 20


def truncate_text(text: str, max_chars: int = DEFAULT_TRUNCATE_CHARS) -> str:
    """Truncate text to a bounded length."""

    if len(text) <= max_chars:
        return text
    suffix = f" {TRUNCATED_VALUE}"
    if max_chars <= len(suffix):
        return suffix[:max_chars]
    return f"{text[: max_chars - len(suffix)]}{suffix}"


def preview_text(text: str, max_chars: int = DEFAULT_PREVIEW_CHARS) -> str:
    """Return a redacted, bounded preview string."""

    return truncate_text(redact_text(text), max_chars=max_chars)


def hash_text(text: str) -> str:
    """Return a stable SHA-256 digest prefix for text."""

    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _type_name(value: Any) -> str:
    if value is None:
        return "none"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    if isinstance(value, Mapping):
        return "dict"
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return "list"
    return type(value).__name__


def _size_of(value: Any) -> int | None:
    if isinstance(value, (Mapping, Sequence)) and not isinstance(
        value, (str, bytes, bytearray)
    ):
        return len(value)
    if isinstance(value, str):
        return len(value)
    return None


def _preview_scalar(value: Any, *, max_chars: int) -> Any:
    if isinstance(value, str):
        return preview_text(value, max_chars=max_chars)
    if isinstance(value, (bool, int, float)) or value is None:
        return value
    return preview_text(str(value), max_chars=max_chars)


def summarize_sequence(
    value: Sequence[Any],
    max_items: int = DEFAULT_MAX_ITEMS,
    *,
    max_depth: int = DEFAULT_MAX_DEPTH,
) -> list[Any]:
    """Return a bounded preview for a sequence."""

    items = list(value)[:max_items]
    return [
        summarize_value(item, max_depth=max_depth - 1, max_items=max_items)
        for item in items
    ]


def summarize_value(
    value: Any,
    *,
    max_depth: int = DEFAULT_MAX_DEPTH,
    max_items: int = DEFAULT_MAX_ITEMS,
) -> Any:
    """Summarize a nested value without returning raw payloads."""

    if max_depth < 0:
        return TRUNCATED_VALUE
    if isinstance(value, Mapping):
        return summarize_mapping(value, max_depth=max_depth, max_items=max_items)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return summarize_sequence(value, max_items=max_items, max_depth=max_depth)
    if isinstance(value, str):
        return _preview_scalar(value, max_chars=DEFAULT_PREVIEW_CHARS)
    return _preview_scalar(value, max_chars=DEFAULT_PREVIEW_CHARS)


def summarize_mapping(
    value: Mapping[str, Any],
    max_depth: int = DEFAULT_MAX_DEPTH,
    max_items: int = DEFAULT_MAX_ITEMS,
) -> dict[str, Any]:
    """Return a bounded summary for a mapping."""

    redacted = redact_mapping(value, max_depth=max_depth)
    items = list(redacted.items())
    summary: dict[str, Any] = {
        "keys": [],
        "types": {},
        "sizes": {},
        "preview": {},
        "count": len(items),
    }
    if len(items) > max_items:
        summary["truncated"] = True
        summary["omitted_count"] = len(items) - max_items
        summary["truncation_reason"] = "item_limit"
    for key, nested_value in items[:max_items]:
        key_name = str(key)
        key_label = REDACTED_VALUE if is_sensitive_key(key_name) else key_name
        summary["keys"].append(key_label)
        summary["types"][key_label] = _type_name(nested_value)
        size = _size_of(nested_value)
        if size is not None:
            summary["sizes"][key_label] = size
        summary["preview"][key_label] = summarize_value(
            nested_value, max_depth=max_depth - 1, max_items=max_items
        )
    return summary


def summarize_display_value(value: Any, *, max_items: int = DEFAULT_MAX_ITEMS) -> Any:
    """Return a display-safe summary without previewing raw payload contents."""

    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        preview = preview_text(value)
        return {
            "value_type": "str",
            "length": len(value),
            "preview": preview,
            "truncated": len(value) > DEFAULT_PREVIEW_CHARS,
            "omitted_count": max(0, len(value) - DEFAULT_PREVIEW_CHARS),
            "truncation_reason": "character_limit"
            if len(value) > DEFAULT_PREVIEW_CHARS
            else "",
        }
    if isinstance(value, Mapping):
        redacted = redact_mapping(value, max_depth=DEFAULT_MAX_DEPTH)
        items = list(redacted.items())
        summary: dict[str, Any] = {
            "value_type": "dict",
            "size": len(items),
            "count": len(items),
            "keys": [],
            "types": {},
            "sizes": {},
            "preview": {},
        }
        if len(items) > max_items:
            summary["truncated"] = True
            summary["omitted_count"] = len(items) - max_items
            summary["truncation_reason"] = "item_limit"
        for key, nested_value in items[:max_items]:
            key_name = str(key)
            key_label = REDACTED_VALUE if is_sensitive_key(key_name) else key_name
            summary["keys"].append(key_label)
            summary["types"][key_label] = _type_name(nested_value)
            size = _size_of(nested_value)
            if size is not None:
                summary["sizes"][key_label] = size
            summary["preview"][key_label] = summarize_value(
                nested_value, max_depth=1, max_items=max_items
            )
        return summary
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        items = list(value)
        summary = {
            "value_type": "list",
            "size": len(items),
            "count": len(items),
            "item_types": [],
            "preview": [],
        }
        if len(items) > max_items:
            summary["truncated"] = True
            summary["omitted_count"] = len(items) - max_items
            summary["truncation_reason"] = "item_limit"
        summary["item_types"] = [_type_name(item) for item in items[:max_items]]
        summary["preview"] = [
            summarize_value(item, max_depth=1, max_items=max_items)
            for item in items[:max_items]
        ]
        return summary
    return {"value_type": _type_name(value)}


def summarize_messages(messages: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize chat-style messages without returning full prompt text."""

    roles: list[str] = []
    preview_parts: list[str] = []
    message_previews: list[dict[str, str]] = []
    for message in messages:
        role = str(message.get("role", ""))
        if role:
            roles.append(role)
        content = message.get("content", "")
        if isinstance(content, str):
            content_preview = preview_text(content, max_chars=120)
        else:
            content_preview = preview_text(
                json.dumps(
                    redact_mapping({"content": content}),
                    ensure_ascii=False,
                    sort_keys=True,
                    default=str,
                ),
                max_chars=120,
            )
        preview_parts.append(f"{role}: {content_preview}".strip())
        message_previews.append({"role": role or "unknown", "preview": content_preview})
    prompt_blob = "\n".join(preview_parts)
    prompt_hash_source = json.dumps(
        redact_mapping({"messages": messages}),
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )
    return {
        "message_count": len(messages),
        "roles": roles,
        "messages": message_previews,
        "preview": preview_text(prompt_blob, max_chars=DEFAULT_PREVIEW_CHARS),
        "prompt_hash": hash_text(prompt_hash_source),
    }
