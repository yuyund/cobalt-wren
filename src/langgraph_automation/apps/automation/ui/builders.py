'''Builders for dynamic UI page specs.'''

from __future__ import annotations

from collections.abc import Iterable

from django.db.models import Model

from langgraph_automation.apps.automation.ui.actions import build_action_specs
from langgraph_automation.apps.automation.ui.formatters import format_value
from langgraph_automation.apps.automation.ui.redaction import redact_value
from langgraph_automation.apps.automation.ui.registry import get_model_ui_config
from langgraph_automation.apps.automation.ui.specs import DetailPageSpec, FieldSpec, FragmentSpec, FormSpec, ListPageSpec, RelatedSectionSpec, TableSpec


def _is_model_instance(obj: object) -> bool:
    return isinstance(obj, Model)


def _resolve_object(model_key: str, obj_or_id: object, actor: object | None = None) -> object:
    config = get_model_ui_config(model_key)
    if config is None:
        raise LookupError(f'Model {model_key!r} is not registered for UI rendering')
    if _is_model_instance(obj_or_id):
        return obj_or_id
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
        )
        for name in field_names
    ]


def _build_fields(obj: object | None, field_names: list[str], *, readonly: bool) -> list[FieldSpec]:
    if obj is None:
        return _build_placeholder_fields(field_names, readonly=readonly)
    fields: list[FieldSpec] = []
    for name in field_names:
        raw_value = getattr(obj, name, None)
        redacted_value, redacted = redact_value(name, raw_value)
        field_type = _field_type_from_value(redacted_value)
        fields.append(
            FieldSpec(
                name=name,
                label=name.replace('_', ' ').title(),
                raw_value=raw_value,
                display_value=format_value(redacted_value),
                field_type=field_type,
                component=_component_from_field_type(field_type),
                readonly=readonly,
                required=False,
                redacted=redacted,
            )
        )
    return fields


def _build_rows(items: Iterable[object], field_names: list[str], *, readonly: bool) -> list[list[FieldSpec]]:
    return [_build_fields(item, field_names, readonly=readonly) for item in items]


def build_list_page_spec(model_key: str, actor: object | None = None) -> ListPageSpec:
    config = get_model_ui_config(model_key)
    if config is None:
        raise LookupError(f'Model {model_key!r} is not registered for UI rendering')
    items = list(config.list_selector(None, actor))
    columns = _build_fields(items[0], config.list_fields, readonly=True) if items else _build_placeholder_fields(config.list_fields, readonly=True)
    rows = _build_rows(items, config.list_fields, readonly=True) if items else []
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
        table_rows = _build_rows(rows, section_config.columns, readonly=True)
        columns = _build_fields(rows[0], section_config.columns, readonly=True) if rows else _build_placeholder_fields(section_config.columns, readonly=True)
        related_sections.append(
            RelatedSectionSpec(
                model_key=section_config.model_key,
                name=section_config.name,
                title=section_config.title,
                table=TableSpec(columns=columns, rows=table_rows, empty_message=section_config.empty_message),
            )
        )
    return DetailPageSpec(model_key=model_key, object_id=object_id, title=config.title, fields=_build_fields(obj, config.detail_fields, readonly=True), actions=actions, related_sections=related_sections)


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
    table_rows = _build_rows(rows, section_config.columns, readonly=True)
    columns = _build_fields(rows[0], section_config.columns, readonly=True) if rows else _build_placeholder_fields(section_config.columns, readonly=True)
    return FragmentSpec(
        model_key=model_key,
        object_id=object_id,
        fragment_name=fragment_name,
        title=section_config.title,
        table=TableSpec(columns=columns, rows=table_rows, empty_message=section_config.empty_message),
    )
