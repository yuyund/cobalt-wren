"""Semantic, renderer-neutral projections for structured field values."""

from __future__ import annotations
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
import ast
from datetime import date, datetime
from decimal import Decimal
import json

_REDACTED_MARKERS = {"***REDACTED***", "[REDACTED]"}
_TRUNCATED_MARKERS = {"***TRUNCATED***", "[TRUNCATED]"}
_MAX_DEPTH = 5
_MAX_ITEMS = 20
_WRAPPER_KEYS = {
    "preview",
    "input_summary",
    "output_summary",
    "metadata",
    "metrics",
    "value",
    "data",
}


@dataclass(frozen=True)
class KeyValueSpec:
    key: str
    value: "ValueSpec"


@dataclass(frozen=True)
class ValueSpec:
    kind: str
    text: str = ""
    entries: tuple[KeyValueSpec, ...] = ()
    items: tuple["ValueSpec", ...] = ()
    count: int = 0
    truncated: bool = False
    omitted_count: int = 0
    truncation_reason: str = ""
    quality: str = "available"
    detail_url: str = ""
    json_text: str = ""

    @property
    def is_structured(self) -> bool:
        return self.kind in {"mapping", "list"}

    @property
    def summary(self) -> str:
        if self.kind == "mapping":
            return f"{self.count} fields"
        if self.kind == "list":
            return f"{self.count} items"
        return self.text

    @property
    def has_meaningful_value(self) -> bool:
        if self.kind in {"empty", "redacted", "truncated"}:
            return False
        if self.kind == "mapping":
            return any(entry.value.has_meaningful_value for entry in self.entries)
        if self.kind == "list":
            return any(item.has_meaningful_value for item in self.items)
        return bool(self.text) or self.kind in {"boolean", "number", "datetime"}

    @property
    def can_inspect(self) -> bool:
        return bool(self.detail_url)


def parse_summary_value(name: str, value: object) -> object:
    """Parse JSON only for known summary fields; ordinary strings stay text."""
    if not name.endswith("_summary") or not isinstance(value, str) or not value.strip():
        return value
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        try:
            parsed = ast.literal_eval(value)
        except (SyntaxError, ValueError):
            return value
    if isinstance(parsed, (Mapping, list, tuple)):
        return parsed
    return value


def _json_text(value: object) -> str:
    try:
        return json.dumps(
            value, ensure_ascii=False, indent=2, sort_keys=True, default=str
        )
    except (TypeError, ValueError):
        return ""


def _unwrap_wrappers(value: object) -> object:
    current = value
    for _ in range(_MAX_DEPTH + 2):
        if not isinstance(current, Mapping) or len(current) != 1:
            break
        key, nested = next(iter(current.items()))
        if str(key).lower() not in _WRAPPER_KEYS:
            break
        current = nested
    return current


def _summary_envelope(value: Mapping[object, object]) -> object | None:
    keys = value.get("keys")
    types = value.get("types")
    sizes = value.get("sizes")
    if not isinstance(keys, Sequence) or isinstance(keys, (str, bytes, bytearray)):
        return None
    if not isinstance(types, Mapping):
        return None
    if not isinstance(sizes, Mapping):
        return None
    preview = value.get("preview")
    if preview not in (None, "", {}, []):
        return _unwrap_wrappers(preview)
    visible_keys = [str(key) for key in keys][:_MAX_ITEMS]
    if not visible_keys:
        return {}
    schema: dict[str, str] = {}
    for key in visible_keys:
        type_name = str(types.get(key, "value"))
        size = sizes.get(key)
        suffix = ""
        if isinstance(size, int):
            suffix = f" · {size} chars" if type_name == "str" else f" · {size} items"
        schema[key] = f"{type_name}{suffix}"
    return schema


def _parse_structured_preview(value: object) -> object:
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text or text[0] not in "[{":
        return value
    try:
        parsed = json.loads(text)
    except (TypeError, ValueError):
        try:
            parsed = ast.literal_eval(text)
        except (SyntaxError, ValueError):
            return value
    return parsed if isinstance(parsed, (Mapping, list, tuple)) else value


def _normalize_known_summary_shape(value: object) -> object:
    if not isinstance(value, Mapping):
        return value
    summary = value.get("summary")
    if isinstance(summary, Mapping) and "value_type" in value and "size" in value:
        return summary
    if "message_previews" in value and "input_summary" in value:
        return {key: nested for key, nested in value.items() if key != "input_summary"}
    return value


def _normalize_summary(value: object) -> object:
    current = value
    for _ in range(_MAX_DEPTH + 3):
        previous = current
        current = _normalize_known_summary_shape(
            _unwrap_wrappers(_parse_structured_preview(current))
        )
        if isinstance(current, Mapping):
            envelope = _summary_envelope(current)
            if envelope is not None:
                current = envelope
        if current == previous:
            break
    return current


def _summary_metadata(value: object) -> tuple[int, str, bool]:
    if not isinstance(value, Mapping):
        return 0, "", False
    omitted = value.get("omitted_count", 0)
    reason = value.get("truncation_reason", "")
    return (
        omitted if isinstance(omitted, int) else 0,
        str(reason or ""),
        bool(value.get("truncated", False)),
    )


def _project_with_metadata(
    value: object, *, depth: int, root_json_text: str = ""
) -> ValueSpec:
    omitted, reason, marked_truncated = _summary_metadata(value)
    normalized = _normalize_summary(value)
    spec = _project_value(normalized, depth=depth, root_json_text=root_json_text)
    if omitted or reason or marked_truncated:
        quality = "partial" if spec.has_meaningful_value else "unavailable"
        spec = replace(
            spec,
            truncated=True,
            omitted_count=omitted,
            truncation_reason=reason or spec.truncation_reason or "bounded_limit",
            quality=quality,
        )
    return spec


def _project_value(value: object, *, depth: int, root_json_text: str = "") -> ValueSpec:
    if value is None or value == "":
        return ValueSpec(kind="empty", quality="empty", json_text=root_json_text)
    if isinstance(value, str):
        if value in _REDACTED_MARKERS:
            return ValueSpec(
                kind="redacted",
                text="Redacted",
                quality="redacted",
                json_text=root_json_text,
            )
        if value in _TRUNCATED_MARKERS:
            return ValueSpec(
                kind="truncated",
                text="Preview unavailable",
                truncated=True,
                truncation_reason="historical_summary",
                quality="unavailable",
                json_text=root_json_text,
            )
        return ValueSpec(
            kind="multiline" if "\n" in value else "text",
            text=value,
            json_text=root_json_text,
        )
    if isinstance(value, bool):
        return ValueSpec(
            kind="boolean", text="Yes" if value else "No", json_text=root_json_text
        )
    if isinstance(value, (int, float, Decimal)) and not isinstance(value, bool):
        return ValueSpec(kind="number", text=str(value), json_text=root_json_text)
    if isinstance(value, (datetime, date)):
        return ValueSpec(
            kind="datetime", text=value.isoformat(), json_text=root_json_text
        )
    if depth >= _MAX_DEPTH:
        return ValueSpec(
            kind="truncated",
            text="Further nested data omitted",
            truncated=True,
            truncation_reason="depth_limit",
            quality="partial",
            json_text=root_json_text,
        )
    if isinstance(value, Mapping):
        source = list(value.items())
        visible = source[:_MAX_ITEMS]
        entries = tuple(
            KeyValueSpec(
                key=str(key).replace("_", " ").title(),
                value=_project_with_metadata(nested, depth=depth + 1),
            )
            for key, nested in visible
        )
        truncated = len(source) > _MAX_ITEMS or bool(value.get("truncated", False))
        quality = (
            "partial"
            if truncated or any(entry.value.quality != "available" for entry in entries)
            else "available"
        )
        return ValueSpec(
            kind="mapping",
            entries=entries,
            count=len(source),
            truncated=truncated,
            omitted_count=max(0, len(source) - len(visible)),
            truncation_reason="item_limit" if len(source) > _MAX_ITEMS else "",
            quality=quality,
            json_text=root_json_text,
        )
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        source = list(value)
        visible = source[:_MAX_ITEMS]
        items = tuple(_project_with_metadata(item, depth=depth + 1) for item in visible)
        truncated = len(source) > _MAX_ITEMS
        return ValueSpec(
            kind="list",
            items=items,
            count=len(source),
            truncated=truncated,
            omitted_count=max(0, len(source) - len(visible)),
            truncation_reason="item_limit" if truncated else "",
            quality="partial"
            if truncated or any(item.quality != "available" for item in items)
            else "available",
            json_text=root_json_text,
        )
    return ValueSpec(kind="text", text=str(value), json_text=root_json_text)


def build_value_spec(value: object, *, depth: int = 0) -> ValueSpec:
    """Build a bounded semantic value tree without renderer-specific classes."""
    original_json = (
        _json_text(value) if isinstance(value, (Mapping, list, tuple)) else ""
    )
    return _project_with_metadata(value, depth=depth, root_json_text=original_json)
