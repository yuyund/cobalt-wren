"""Renderer-neutral diagnostic detail resolution for registered UI records."""

from __future__ import annotations
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from cobalt_wren.apps.automation.services.diagnostics import (
    active_diagnostic,
    build_bounded_diagnostic,
)
from cobalt_wren.apps.automation.ui.values import ValueSpec, build_value_spec

_SOURCE_FIELDS: dict[str, dict[str, str | None]] = {
    "workflows": {"definition_payload_summary": "definition_payload"},
    "runs": {
        "input_payload_summary": "input_payload",
        "output_payload_summary": "output_payload",
    },
    "spans": {
        "input_summary": None,
        "output_summary": None,
        "metrics_summary": "metrics",
        "metadata_summary": "metadata",
    },
    "events": {"payload_summary": "payload"},
    "artifacts": {"metadata_summary": "metadata"},
    "checkpoints": {"state_summary": None},
}


@dataclass(frozen=True)
class DiagnosticDetailSpec:
    title: str
    value: ValueSpec
    byte_size: int
    truncated: bool
    truncation_reason: str
    source: str


def diagnostic_permission(model_key: str) -> str:
    return f"automation.view_{model_key.rstrip('s')}"


def _is_summary_envelope(value: object) -> bool:
    if not isinstance(value, Mapping):
        return False
    keys = value.get("keys")
    types = value.get("types")
    sizes = value.get("sizes")
    return (
        isinstance(keys, Sequence)
        and not isinstance(keys, (str, bytes, bytearray))
        and isinstance(types, Mapping)
        and isinstance(sizes, Mapping)
    )


def _raw_source(model_key: str, obj: object, field_name: str) -> object | None:
    source_name = _SOURCE_FIELDS.get(model_key, {}).get(field_name)
    return getattr(obj, source_name, None) if source_name else None


def resolve_diagnostic_detail(
    model_key: str, obj: object, field_name: str
) -> DiagnosticDetailSpec | None:
    object_id = getattr(obj, "pk", None)
    if not isinstance(object_id, int) or field_name not in _SOURCE_FIELDS.get(
        model_key, {}
    ):
        return None
    stored = active_diagnostic(
        target_type=model_key, target_id=object_id, field_name=field_name
    )
    if stored is not None:
        value = build_value_spec(stored.payload)
        if value.has_meaningful_value:
            return DiagnosticDetailSpec(
                title=field_name.replace("_summary", "").replace("_", " ").title(),
                value=value,
                byte_size=stored.byte_size,
                truncated=stored.truncated,
                truncation_reason=stored.truncation_reason,
                source="retained diagnostic snapshot",
            )
    raw = _raw_source(model_key, obj, field_name)
    if raw in (None, "", {}, []) or _is_summary_envelope(raw):
        return None
    source_preview = build_value_spec(raw)
    if not source_preview.has_meaningful_value:
        return None
    bounded = build_bounded_diagnostic(raw)
    value = build_value_spec(bounded.payload)
    if not value.has_meaningful_value:
        return None
    return DiagnosticDetailSpec(
        title=field_name.replace("_summary", "").replace("_", " ").title(),
        value=value,
        byte_size=bounded.byte_size,
        truncated=bounded.truncated,
        truncation_reason=bounded.truncation_reason,
        source="bounded control-plane value",
    )


def attach_diagnostic_url(
    model_key: str, obj: object, field_name: str, value: ValueSpec
) -> ValueSpec:
    if resolve_diagnostic_detail(model_key, obj, field_name) is None:
        return value
    object_id = getattr(obj, "pk", None)
    return replace(
        value, detail_url=f"/ui/diagnostics/{model_key}/{object_id}/{field_name}/"
    )
