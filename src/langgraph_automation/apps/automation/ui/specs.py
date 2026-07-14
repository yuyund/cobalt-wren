'''UI specification dataclasses for dynamic rendering.'''

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FieldSpec:
    name: str
    label: str
    raw_value: object
    display_value: str
    field_type: str
    component: str
    readonly: bool
    required: bool
    visible: bool = True
    help_text: str | None = None
    redacted: bool = False


@dataclass(frozen=True)
class ActionSpec:
    name: str
    label: str
    url: str
    method: str
    enabled: bool = True
    visible: bool = True
    danger: bool = False
    confirm: str | None = None
    hx_target: str | None = None
    disabled_reason: str | None = None


@dataclass(frozen=True)
class TableSpec:
    columns: list[FieldSpec] = field(default_factory=list)
    rows: list[list[FieldSpec]] = field(default_factory=list)
    empty_message: str = 'No records found'


@dataclass(frozen=True)
class RelatedSectionSpec:
    model_key: str
    name: str
    title: str
    table: TableSpec
    actions: list[ActionSpec] = field(default_factory=list)


@dataclass(frozen=True)
class ListPageSpec:
    model_key: str
    title: str
    columns: list[FieldSpec] = field(default_factory=list)
    rows: list[list[FieldSpec]] = field(default_factory=list)
    actions: list[ActionSpec] = field(default_factory=list)
    empty_message: str = 'No records found'


@dataclass(frozen=True)
class DetailPageSpec:
    model_key: str
    object_id: int | None
    title: str
    fields: list[FieldSpec] = field(default_factory=list)
    actions: list[ActionSpec] = field(default_factory=list)
    related_sections: list[RelatedSectionSpec] = field(default_factory=list)


@dataclass(frozen=True)
class FormSpec:
    model_key: str
    object_id: int | None
    title: str
    fields: list[FieldSpec] = field(default_factory=list)
    actions: list[ActionSpec] = field(default_factory=list)
    submit_label: str = 'Save'


@dataclass(frozen=True)
class FragmentSpec:
    model_key: str
    object_id: int | None
    fragment_name: str
    title: str
    table: TableSpec
