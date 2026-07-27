'''Builders for dynamic UI page specs.'''

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import replace

from django.db.models import Model
from django.utils.text import slugify

from cobalt_wren.apps.automation.models.integration_projection import IntegrationProjectionRecord
from cobalt_wren.apps.automation.ui.actions import build_action_specs
from cobalt_wren.apps.automation.ui.formatters import format_value
from cobalt_wren.apps.automation.ui.diagnostics import attach_diagnostic_url
from cobalt_wren.apps.automation.ui.redaction import redact_value
from cobalt_wren.core.summary import summarize_display_value
from cobalt_wren.apps.automation.ui.registry import get_model_ui_config
from cobalt_wren.apps.automation.ui.specs import (
    DetailPageSpec,
    FieldSpec,
    FragmentSpec,
    FormSpec,
    IntegrationCurrentStateSpec,
    IntegrationSummarySpec,
    IntegrationTimelineItemSpec,
    ListPageSpec,
    ProjectionSectionSpec,
    RelatedSectionSpec,
    TableSpec,
)
from cobalt_wren.apps.automation.ui.values import build_value_spec, parse_summary_value
from cobalt_wren.apps.automation.services.integration_projections import (
    active_projections_for_run,
    active_projections_for_span,
)


def _is_model_instance(obj: object) -> bool:
    return isinstance(obj, Model)


def _resolve_object(model_key: str, obj_or_id: object, actor: object | None = None) -> object:
    config = get_model_ui_config(model_key)
    if config is None:
        raise LookupError(f'Model {model_key!r} is not registered for UI rendering')
    if _is_model_instance(obj_or_id):
        return obj_or_id
    if not isinstance(obj_or_id, (str, int)) or isinstance(obj_or_id, bool):
        raise TypeError("object identifier must be a string or integer")
    resolved = config.detail_selector(int(obj_or_id), actor)
    if resolved is None:
        raise LookupError(f'Object {model_key!r}:{obj_or_id!r} was not found')
    return resolved


def _field_type_from_value(value: object) -> str:
    if value is None:
        return 'text'
    if isinstance(value, bool):
        return 'boolean'
    if isinstance(value, (int, float)):
        return 'number'
    if isinstance(value, (dict, list, tuple)):
        return 'json'
    return 'text'


def _component_from_field_type(field_type: str) -> str:
    return {
        'json': 'json',
        'boolean': 'badge',
        'number': 'text',
        'text': 'text',
    }.get(field_type, 'text')


def _build_placeholder_fields(field_names: list[str], *, readonly: bool) -> list[FieldSpec]:
    return [
        FieldSpec(
            name=name,
            label=name.replace('_', ' ').title(),
            raw_value=None,
            display_value='',
            field_type='text',
            component='text',
            readonly=readonly,
            required=False,
            value=build_value_spec(None),
        )
        for name in field_names
    ]


def _build_fields(obj: object | None, field_names: list[str], *, readonly: bool, model_key: str | None = None, diagnostics: bool = False) -> list[FieldSpec]:
    if obj is None:
        return _build_placeholder_fields(field_names, readonly=readonly)
    fields: list[FieldSpec] = []
    for name in field_names:
        raw_value = getattr(obj, name, None)
        if name.endswith('_summary'):
            safe_value = raw_value
            redacted = False
        elif isinstance(raw_value, Mapping) or (isinstance(raw_value, Sequence) and not isinstance(raw_value, (str, bytes, bytearray))):
            safe_value = summarize_display_value(raw_value)
            redacted = True
        else:
            safe_value, redacted = redact_value(name, raw_value)
        projected_value = parse_summary_value(name, safe_value)
        field_type = _field_type_from_value(projected_value)
        value_spec = build_value_spec(projected_value)
        if diagnostics and model_key is not None:
            value_spec = attach_diagnostic_url(model_key, obj, name, value_spec)
        fields.append(
            FieldSpec(
                name=name,
                label=name.replace('_', ' ').title(),
                raw_value=raw_value,
                display_value=format_value(safe_value),
                field_type=field_type,
                component=_component_from_field_type(field_type),
                readonly=readonly,
                required=False,
                redacted=redacted,
                value=value_spec,
            )
        )
    return fields


def _build_rows(items: Iterable[object], field_names: list[str], *, readonly: bool, model_key: str) -> list[list[FieldSpec]]:
    rows: list[list[FieldSpec]] = []
    for item in items:
        fields = _build_fields(item, field_names, readonly=readonly)
        object_id = getattr(item, "pk", None)
        if fields and isinstance(object_id, int):
            fields[0] = replace(fields[0], url=f"/ui/{model_key}/{object_id}/")
        rows.append(fields)
    return rows


def _projection_records(
    model_key: str, obj: object
) -> list[IntegrationProjectionRecord]:
    object_id = getattr(obj, "pk", None)
    if not isinstance(object_id, int):
        return []
    if model_key == "runs":
        return list(active_projections_for_run(object_id))
    if model_key == "spans":
        return list(active_projections_for_span(object_id))
    return []


def _integration_anchor(integration_id: str) -> str:
    return f"integration-{slugify(integration_id) or 'unknown'}"


def _build_integration_summaries(
    records: list[IntegrationProjectionRecord],
) -> list[IntegrationSummarySpec]:
    grouped: dict[str, list[IntegrationProjectionRecord]] = {}
    for record in records:
        integration_id = str(getattr(record, "integration_id", "unknown"))
        grouped.setdefault(integration_id, []).append(record)
    summaries: list[IntegrationSummarySpec] = []
    for integration_id, items in grouped.items():
        execution_units = {
            _projection_subject_id(item)
            for item in items
            if item.subject_kind == "execution_unit"
        }
        interactions = {
            _projection_subject_id(item)
            for item in items
            if item.subject_kind == "interaction"
        }
        checkpoints = {
            _projection_subject_id(item)
            for item in items
            if item.subject_kind == "checkpoint"
            or "checkpoint" in str(getattr(item, "schema_id", "")).lower()
        }
        latest_status = ""
        for item in reversed(items):
            payload = getattr(item, "payload", None)
            status = payload.get("status") if isinstance(payload, Mapping) else None
            if isinstance(status, str) and status.strip().lower() in {
                "running",
                "succeeded",
                "failed",
                "waiting",
                "paused",
                "completed",
                "cancelled",
            }:
                latest_status = status.strip().lower()
                break
        summaries.append(
            IntegrationSummarySpec(
                integration_id=integration_id,
                anchor_id=_integration_anchor(integration_id),
                projection_count=len(items),
                execution_unit_count=len(execution_units),
                interaction_count=len(interactions),
                checkpoint_count=len(checkpoints),
                schema_ids=tuple(sorted({str(getattr(item, "schema_id", "")) for item in items})),
                latest_status=latest_status,
                truncated_count=sum(bool(getattr(item, "truncated", False)) for item in items),
            )
        )
    return sorted(summaries, key=lambda item: item.integration_id)


def _projection_status(record: IntegrationProjectionRecord) -> str:
    payload = record.payload
    status = payload.get("status") if isinstance(payload, Mapping) else None
    if not isinstance(status, str):
        return ""
    normalized = status.strip().lower()
    return "succeeded" if normalized == "not_running" else normalized


def _projection_subject_id(record: IntegrationProjectionRecord) -> str:
    return record.subject_external_id or record.owner_external_id or str(record.pk)


def _build_current_state(
    records: list[IntegrationProjectionRecord],
) -> list[IntegrationCurrentStateSpec]:
    latest: dict[tuple[str, str, str, str], IntegrationProjectionRecord] = {}
    for record in records:
        if record.projection_kind != "snapshot":
            continue
        key = (
            record.integration_id,
            record.subject_kind,
            _projection_subject_id(record),
            record.schema_id,
        )
        previous = latest.get(key)
        if previous is None or (record.occurred_at, record.sequence, record.pk) > (
            previous.occurred_at,
            previous.sequence,
            previous.pk,
        ):
            latest[key] = record
    return [
        IntegrationCurrentStateSpec(
            integration_id=record.integration_id,
            subject_kind=record.subject_kind,
            subject_external_id=_projection_subject_id(record),
            title=record.title or _projection_subject_id(record),
            status=_projection_status(record),
            schema_id=record.schema_id,
            occurred_at=record.occurred_at,
            detail_anchor_id=f"projection-{record.pk}",
        )
        for record in sorted(
            latest.values(),
            key=lambda item: (item.integration_id, item.subject_kind, _projection_subject_id(item)),
        )
    ]


def _build_timeline(
    records: list[IntegrationProjectionRecord],
) -> list[IntegrationTimelineItemSpec]:
    timeline_records = [
        record
        for record in records
        if record.projection_kind in {"snapshot", "event"}
    ]
    timeline_records.sort(key=lambda item: (item.occurred_at, item.sequence, item.pk))
    return [
        IntegrationTimelineItemSpec(
            integration_id=record.integration_id,
            projection_kind=record.projection_kind,
            subject_kind=record.subject_kind,
            subject_external_id=_projection_subject_id(record),
            title=record.title or record.schema_id,
            status=_projection_status(record),
            schema_id=record.schema_id,
            occurred_at=record.occurred_at,
            detail_anchor_id=f"projection-{record.pk}",
        )
        for record in timeline_records
    ]


def _build_projection_sections(
    records: list[IntegrationProjectionRecord],
) -> list[ProjectionSectionSpec]:
    sections: list[ProjectionSectionSpec] = []
    for record in records:
        value = build_value_spec(record.payload_summary)
        sections.append(
            ProjectionSectionSpec(
                integration_id=record.integration_id,
                schema_id=record.schema_id,
                title=record.title or record.schema_id,
                owner_kind=record.owner_kind,
                owner_external_id=record.owner_external_id,
                created_at=record.created_at,
                anchor_id=f"projection-{record.pk}",
                payload=FieldSpec(
                    name="payload",
                    label="Details",
                    raw_value=record.payload,
                    display_value=format_value(record.payload_summary),
                    field_type="json",
                    component="json",
                    readonly=True,
                    required=False,
                    redacted=True,
                    value=value,
                ),
                truncated=record.truncated,
                classification=record.classification,
            )
        )
    return sections


def build_list_page_spec(model_key: str, actor: object | None = None) -> ListPageSpec:
    config = get_model_ui_config(model_key)
    if config is None:
        raise LookupError(f'Model {model_key!r} is not registered for UI rendering')
    items = list(config.list_selector(None, actor))
    columns = _build_fields(items[0], config.list_fields, readonly=True) if items else _build_placeholder_fields(config.list_fields, readonly=True)
    rows = _build_rows(items, config.list_fields, readonly=True, model_key=model_key) if items else []
    return ListPageSpec(model_key=model_key, title=config.title, columns=columns, rows=rows, actions=[])


def build_detail_page_spec(model_key: str, obj_or_id: object, *, actor: object | None = None) -> DetailPageSpec:
    config = get_model_ui_config(model_key)
    if config is None:
        raise LookupError(f'Model {model_key!r} is not registered for UI rendering')
    obj = _resolve_object(model_key, obj_or_id, actor=actor)
    object_id = getattr(obj, 'pk', None)
    actions = build_action_specs(model_key, obj, actor=actor)
    related_sections: list[RelatedSectionSpec] = []
    for section_config in config.related_sections:
        rows = list(section_config.selector(obj, actor))
        table_rows = _build_rows(rows, section_config.columns, readonly=True, model_key=section_config.model_key)
        columns = _build_fields(rows[0], section_config.columns, readonly=True) if rows else _build_placeholder_fields(section_config.columns, readonly=True)
        related_sections.append(
            RelatedSectionSpec(
                model_key=section_config.model_key,
                name=section_config.name,
                title=section_config.title,
                table=TableSpec(columns=columns, rows=table_rows, empty_message=section_config.empty_message),
            )
        )
    projection_records = _projection_records(model_key, obj)
    return DetailPageSpec(
        model_key=model_key,
        object_id=object_id,
        title=config.title,
        fields=_build_fields(
            obj,
            config.detail_fields,
            readonly=True,
            model_key=model_key,
            diagnostics=True,
        ),
        actions=actions,
        related_sections=related_sections,
        integration_summaries=_build_integration_summaries(projection_records),
        integration_current_state=_build_current_state(projection_records),
        integration_timeline=_build_timeline(projection_records),
        projection_sections=_build_projection_sections(projection_records),
    )


def build_form_spec(model_key: str, obj_or_id: object | None = None, *, actor: object | None = None) -> FormSpec:
    config = get_model_ui_config(model_key)
    if config is None:
        raise LookupError(f'Model {model_key!r} is not registered for UI rendering')
    if obj_or_id is None:
        fields = _build_placeholder_fields(config.list_fields, readonly=False)
        object_id = None
    else:
        obj = _resolve_object(model_key, obj_or_id, actor=actor)
        fields = _build_fields(obj, config.detail_fields, readonly=False)
        object_id = getattr(obj, 'pk', None)
    return FormSpec(model_key=model_key, object_id=object_id, title=config.title, fields=fields, actions=[])


def build_fragment_spec(model_key: str, object_id: int, fragment_name: str, *, actor: object | None = None) -> FragmentSpec:
    config = get_model_ui_config(model_key)
    if config is None:
        raise LookupError(f'Model {model_key!r} is not registered for UI rendering')
    obj = config.detail_selector(object_id, actor)
    if obj is None:
        raise LookupError(f'Object {model_key!r}:{object_id!r} was not found')
    section_config = next((section for section in config.related_sections if section.name == fragment_name), None)
    if section_config is None:
        raise LookupError(f'Fragment {fragment_name!r} is not registered for {model_key!r}')
    rows = list(section_config.selector(obj, actor))
    table_rows = _build_rows(rows, section_config.columns, readonly=True, model_key=section_config.model_key)
    columns = _build_fields(rows[0], section_config.columns, readonly=True) if rows else _build_placeholder_fields(section_config.columns, readonly=True)
    return FragmentSpec(
        model_key=model_key,
        object_id=object_id,
        fragment_name=fragment_name,
        title=section_config.title,
        table=TableSpec(columns=columns, rows=table_rows, empty_message=section_config.empty_message),
    )
