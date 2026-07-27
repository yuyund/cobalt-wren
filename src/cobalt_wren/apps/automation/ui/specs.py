'''UI specification dataclasses for dynamic rendering.'''

from __future__ import annotations

from dataclasses import dataclass, field

from cobalt_wren.apps.automation.ui.values import ValueSpec


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
    choices: tuple[str, ...] = ()
    url: str | None = None
    value: ValueSpec = field(default_factory=lambda: ValueSpec(kind="empty"))


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
    input_fields: list[FieldSpec] = field(default_factory=list)
    hidden_fields: dict[str, str] = field(default_factory=dict)


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
class IntegrationSummarySpec:
    integration_id: str
    anchor_id: str
    projection_count: int
    execution_unit_count: int
    interaction_count: int
    checkpoint_count: int
    schema_ids: tuple[str, ...]
    latest_status: str = ""
    truncated_count: int = 0


@dataclass(frozen=True)
class IntegrationCurrentStateSpec:
    integration_id: str
    subject_kind: str
    subject_external_id: str
    title: str
    status: str
    schema_id: str
    occurred_at: object
    detail_anchor_id: str


@dataclass(frozen=True)
class IntegrationTimelineItemSpec:
    integration_id: str
    projection_kind: str
    subject_kind: str
    subject_external_id: str
    title: str
    status: str
    schema_id: str
    occurred_at: object
    detail_anchor_id: str


@dataclass(frozen=True)
class ProjectionSectionSpec:
    integration_id: str
    schema_id: str
    title: str
    owner_kind: str
    owner_external_id: str
    created_at: object
    payload: FieldSpec
    anchor_id: str
    truncated: bool = False
    classification: str = "internal"


@dataclass(frozen=True)
class DetailPageSpec:
    model_key: str
    object_id: int | None
    title: str
    fields: list[FieldSpec] = field(default_factory=list)
    actions: list[ActionSpec] = field(default_factory=list)
    related_sections: list[RelatedSectionSpec] = field(default_factory=list)
    integration_summaries: list[IntegrationSummarySpec] = field(default_factory=list)
    integration_current_state: list[IntegrationCurrentStateSpec] = field(default_factory=list)
    integration_timeline: list[IntegrationTimelineItemSpec] = field(default_factory=list)
    projection_sections: list[ProjectionSectionSpec] = field(default_factory=list)


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
