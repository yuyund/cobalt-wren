"""Renderer-neutral semantic layouts for selected control-plane detail pages."""

from __future__ import annotations
from dataclasses import dataclass
from cobalt_wren.apps.automation.ui.specs import DetailPageSpec, FieldSpec


@dataclass(frozen=True)
class DetailSectionLayout:
    key: str
    title: str
    description: str
    fields: tuple[str, ...]


@dataclass(frozen=True)
class DetailLayoutSpec:
    primary: tuple[str, ...]
    sections: tuple[DetailSectionLayout, ...]
    technical: tuple[str, ...] = ()


@dataclass(frozen=True)
class DetailSectionSpec:
    key: str
    title: str
    description: str
    fields: tuple[FieldSpec, ...]


@dataclass(frozen=True)
class DetailPresentationSpec:
    model_key: str
    primary_fields: tuple[FieldSpec, ...]
    sections: tuple[DetailSectionSpec, ...]
    technical_fields: tuple[FieldSpec, ...]


_LAYOUTS = {
    "spans": DetailLayoutSpec(
        primary=(
            "run",
            "parent",
            "span_type",
            "name",
            "status",
            "node_name",
            "attempt",
            "started_at",
            "finished_at",
            "duration_ms",
        ),
        sections=(
            DetailSectionLayout(
                "span.input",
                "Input",
                "Bounded input summary recorded for this execution span.",
                ("input_summary",),
            ),
            DetailSectionLayout(
                "span.output",
                "Output",
                "Bounded output summary produced by this execution span.",
                ("output_summary",),
            ),
            DetailSectionLayout(
                "span.error",
                "Error",
                "Failure information recorded by the execution boundary.",
                ("error_message",),
            ),
            DetailSectionLayout(
                "span.metrics",
                "Metrics",
                "Performance and usage measurements emitted by the span.",
                ("metrics_summary",),
            ),
            DetailSectionLayout(
                "span.metadata",
                "Metadata",
                "Additional bounded observability context.",
                ("metadata_summary",),
            ),
        ),
        technical=("external_trace_id", "external_span_id", "created_at", "updated_at"),
    ),
    "events": DetailLayoutSpec(
        primary=("run", "span", "event_type", "level", "node_name", "created_at"),
        sections=(
            DetailSectionLayout(
                "event.message",
                "Message",
                "Human-readable event description.",
                ("message",),
            ),
            DetailSectionLayout(
                "event.payload",
                "Payload",
                "Bounded event context retained for diagnostics.",
                ("payload_summary",),
            ),
        ),
    ),
    "artifacts": DetailLayoutSpec(
        primary=("run", "span", "name", "kind", "content_type", "size", "created_at"),
        sections=(
            DetailSectionLayout(
                "artifact.location",
                "Storage",
                "External artifact location and identifier.",
                ("storage_key",),
            ),
            DetailSectionLayout(
                "artifact.metadata",
                "Metadata",
                "Bounded metadata describing the artifact.",
                ("metadata_summary",),
            ),
        ),
    ),
    "checkpoints": DetailLayoutSpec(
        primary=("run", "span", "backend", "node_name", "created_at"),
        sections=(
            DetailSectionLayout(
                "checkpoint.identity",
                "Checkpoint identity",
                "Identifiers used to locate and resume this checkpoint.",
                ("thread_id", "checkpoint_id", "checkpoint_namespace"),
            ),
            DetailSectionLayout(
                "checkpoint.state",
                "State",
                "Bounded state summary retained by the checkpoint integration.",
                ("state_summary",),
            ),
        ),
    ),
}


def _select(
    fields: dict[str, FieldSpec], names: tuple[str, ...]
) -> tuple[FieldSpec, ...]:
    return tuple(fields[name] for name in names if name in fields)


def _has_content(field: FieldSpec) -> bool:
    value = field.value
    if value.kind == "empty" or (
        value.kind in {"mapping", "list"} and value.count == 0
    ):
        return False
    return value.has_meaningful_value or value.can_inspect


def build_detail_presentation(page: DetailPageSpec) -> DetailPresentationSpec | None:
    layout = _LAYOUTS.get(page.model_key)
    if layout is None:
        return None
    fields = {field.name: field for field in page.fields}
    sections = tuple(
        DetailSectionSpec(section.key, section.title, section.description, selected)
        for section in layout.sections
        if (
            selected := tuple(
                field
                for field in _select(fields, section.fields)
                if _has_content(field)
            )
        )
    )
    return DetailPresentationSpec(
        model_key=page.model_key,
        primary_fields=_select(fields, layout.primary),
        sections=sections,
        technical_fields=_select(fields, layout.technical),
    )
