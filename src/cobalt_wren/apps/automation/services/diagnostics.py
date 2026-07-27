"""Safe bounded diagnostic snapshot persistence."""

from __future__ import annotations
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import timedelta
import json
from typing import Any
from django.conf import settings
from django.utils import timezone
from cobalt_wren.apps.automation.models.diagnostic import DiagnosticPayload
from cobalt_wren.apps.automation.models.run import Run
from cobalt_wren.core.redaction import (
    REDACTED_VALUE,
    is_sensitive_key,
    redact_text,
)

_MAX_BYTES = 64 * 1024
_MAX_DEPTH = 8
_MAX_ITEMS = 100
_MAX_TEXT_CHARS = 2000


@dataclass(frozen=True)
class BoundedDiagnostic:
    payload: object
    byte_size: int
    truncated: bool
    truncation_reason: str


def _bound(
    value: Any, *, depth: int, max_items: int, max_chars: int
) -> tuple[Any, bool]:
    if isinstance(value, str):
        safe = redact_text(value)
        if len(safe) > max_chars:
            return safe[:max_chars] + "…", True
        return safe, False
    if isinstance(value, Mapping):
        if depth >= _MAX_DEPTH:
            return {"_omitted": "maximum depth reached"}, True
        mapping_result: dict[str, Any] = {}
        truncated = len(value) > max_items
        for index, (key, nested) in enumerate(value.items()):
            if index >= max_items:
                break
            key_name = str(key)
            if is_sensitive_key(key_name):
                mapping_result[key_name] = REDACTED_VALUE
                continue
            bounded, nested_truncated = _bound(
                nested, depth=depth + 1, max_items=max_items, max_chars=max_chars
            )
            mapping_result[key_name] = bounded
            truncated = truncated or nested_truncated
        if len(value) > max_items:
            mapping_result["_omitted_count"] = len(value) - max_items
        return mapping_result, truncated
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        source = list(value)
        sequence_result: list[Any] = []
        truncated = len(source) > max_items
        for item in source[:max_items]:
            bounded, nested_truncated = _bound(
                item, depth=depth + 1, max_items=max_items, max_chars=max_chars
            )
            sequence_result.append(bounded)
            truncated = truncated or nested_truncated
        if len(source) > max_items:
            sequence_result.append({"_omitted_count": len(source) - max_items})
        return sequence_result, truncated
    if value is None or isinstance(value, (bool, int, float)):
        return value, False
    return _bound(str(value), depth=depth, max_items=max_items, max_chars=max_chars)


def build_bounded_diagnostic(value: object) -> BoundedDiagnostic:
    reason = ""
    for max_items, max_chars in ((_MAX_ITEMS, _MAX_TEXT_CHARS), (25, 500), (10, 200)):
        payload, truncated = _bound(
            value, depth=0, max_items=max_items, max_chars=max_chars
        )
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode()
        if len(encoded) <= _MAX_BYTES:
            if truncated:
                reason = "bounded_limit"
            return BoundedDiagnostic(
                payload=payload,
                byte_size=len(encoded),
                truncated=truncated,
                truncation_reason=reason,
            )
    fallback = {
        "preview_unavailable": True,
        "reason": "payload exceeds diagnostic byte limit",
    }
    encoded = json.dumps(fallback, separators=(",", ":")).encode()
    return BoundedDiagnostic(
        payload=fallback,
        byte_size=len(encoded),
        truncated=True,
        truncation_reason="byte_limit",
    )


def diagnostic_retention_days() -> int:
    return max(
        1, int(getattr(settings, "COBALT_WREN_DIAGNOSTIC_RETENTION_DAYS", 7))
    )


def record_diagnostic_payload(
    *,
    target_type: str,
    target_id: int,
    field_name: str,
    value: object,
    run: Run | None = None,
) -> DiagnosticPayload:
    bounded = build_bounded_diagnostic(value)
    expires_at = timezone.now() + timedelta(days=diagnostic_retention_days())
    diagnostic, _created = DiagnosticPayload.objects.update_or_create(
        target_type=target_type[:32],
        target_id=target_id,
        field_name=field_name[:100],
        defaults={
            "run": run,
            "payload": bounded.payload,
            "byte_size": bounded.byte_size,
            "truncated": bounded.truncated,
            "truncation_reason": bounded.truncation_reason,
            "expires_at": expires_at,
        },
    )
    return diagnostic


def active_diagnostic(
    *, target_type: str, target_id: int, field_name: str
) -> DiagnosticPayload | None:
    return DiagnosticPayload.objects.filter(
        target_type=target_type,
        target_id=target_id,
        field_name=field_name,
        expires_at__gt=timezone.now(),
    ).first()
