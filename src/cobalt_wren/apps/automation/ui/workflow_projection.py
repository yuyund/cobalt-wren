"""Safe workflow metadata projection into dynamic UI action specs."""

from __future__ import annotations

from collections.abc import Mapping

from django.http import HttpRequest

from cobalt_wren.apps.automation.models.run import Run
from cobalt_wren.apps.automation.policies.runs import can_resume_run
from cobalt_wren.apps.automation.services import runtime as runtime_module
from cobalt_wren.apps.automation.services.dispatch import dispatch_resume
from cobalt_wren.apps.automation.services.workflow_reference import (
    parse_workflow_reference,
)
from cobalt_wren.apps.automation.ui.specs import ActionSpec, FieldSpec

_MAX_ACTIONS = 10
_MAX_FIELDS = 20
_SUPPORTED_TYPES = {"string", "integer", "number", "boolean"}


def _preview_mapping(run: Run) -> Mapping[str, object]:
    summary = run.output_payload.get("summary")
    if not isinstance(summary, Mapping):
        return {}
    preview = summary.get("preview")
    return preview if isinstance(preview, Mapping) else {}


def _allowed_actions(run: Run) -> set[str] | None:
    value = _preview_mapping(run).get("allowed_actions")
    if isinstance(value, list):
        return {str(item) for item in value}
    return None


def _checkpoint_id(run: Run) -> str | None:
    value = _preview_mapping(run).get("checkpoint_id")
    return value if isinstance(value, str) and value else None


def _prepared(run: Run):
    reference = parse_workflow_reference(run.workflow.definition_payload)
    if reference is None:
        return None
    try:
        return runtime_module.get_run_execution_services().prepare_workflow(reference)
    except Exception:
        return None


def _schema_fields(schema: object) -> list[FieldSpec]:
    if not isinstance(schema, Mapping) or schema.get("type") != "object":
        return []
    properties = schema.get("properties", {})
    if not isinstance(properties, Mapping):
        return []
    required = (
        {str(item) for item in schema.get("required", [])}
        if isinstance(schema.get("required"), list)
        else set()
    )
    fields: list[FieldSpec] = []
    for name, raw in list(properties.items())[:_MAX_FIELDS]:
        if not isinstance(name, str) or not isinstance(raw, Mapping):
            continue
        field_type = str(raw.get("type", "string"))
        if field_type not in _SUPPORTED_TYPES:
            continue
        enum = raw.get("enum")
        choices = tuple(str(item) for item in enum) if isinstance(enum, list) else ()
        component = (
            "textarea"
            if raw.get("format") == "textarea"
            else ("select" if choices else "input")
        )
        fields.append(
            FieldSpec(
                name=name,
                label=str(raw.get("title") or name.replace("_", " ").title()),
                raw_value=None,
                display_value="",
                field_type=field_type,
                component=component,
                readonly=False,
                required=name in required,
                help_text=str(raw.get("description"))
                if raw.get("description")
                else None,
                choices=choices,
            )
        )
    return fields


def build_resume_action_specs(
    run: Run, actor: object | None = None
) -> list[ActionSpec]:
    policy = can_resume_run(actor, run)
    if not policy.allowed:
        return []
    prepared = _prepared(run)
    if prepared is None:
        return []
    raw_actions = prepared.extra.get("resume_actions")
    if not isinstance(raw_actions, Mapping):
        return []
    allowed = _allowed_actions(run)
    checkpoint_id = _checkpoint_id(run)
    specs: list[ActionSpec] = []
    for name, raw in list(raw_actions.items())[:_MAX_ACTIONS]:
        if not isinstance(name, str) or not isinstance(raw, Mapping):
            continue
        if allowed is not None and name not in allowed:
            continue
        hidden = {"resume_action": name}
        if checkpoint_id:
            hidden["checkpoint_id"] = checkpoint_id
        specs.append(
            ActionSpec(
                name=f"resume-{name}",
                label=str(raw.get("title") or name.replace("_", " ").title()),
                url=f"/ui/runs/{run.pk}/actions/resume-{name}/",
                method="POST",
                danger=bool(raw.get("danger", False)),
                confirm=str(raw.get("confirm")) if raw.get("confirm") else None,
                hx_target="#page-root",
                input_fields=_schema_fields(raw.get("schema")),
                hidden_fields=hidden,
            )
        )
    return specs


def _coerce(field: FieldSpec, value: str) -> object:
    if field.field_type == "integer":
        return int(value)
    if field.field_type == "number":
        return float(value)
    if field.field_type == "boolean":
        return value.lower() in {"1", "true", "on", "yes"}
    if field.choices and value not in field.choices:
        raise ValueError(f"Invalid value for {field.label}")
    return value


def dispatch_resume_action(
    run: Run, action_name: str, request: HttpRequest, actor: object | None = None
) -> object:
    policy = can_resume_run(actor, run)
    if not policy.allowed:
        raise PermissionError(policy.reason)
    prepared = _prepared(run)
    if prepared is None:
        raise LookupError("Workflow presentation is unavailable")
    raw_actions = prepared.extra.get("resume_actions")
    if not isinstance(raw_actions, Mapping):
        raise LookupError("Workflow resume actions are unavailable")
    raw = raw_actions.get(action_name)
    if not isinstance(raw, Mapping):
        raise LookupError(f"Unknown resume action: {action_name}")
    allowed = _allowed_actions(run)
    if allowed is not None and action_name not in allowed:
        raise PermissionError("Resume action is not allowed for the current checkpoint")
    fields = _schema_fields(raw.get("schema"))
    payload = (
        dict(raw.get("payload", {})) if isinstance(raw.get("payload"), Mapping) else {}
    )
    for field in fields:
        value = request.POST.get(field.name, "")
        if field.required and not value.strip():
            raise ValueError(f"{field.label} is required")
        if value or field.field_type == "boolean":
            payload[field.name] = _coerce(field, value)
    return dispatch_resume(
        run=run,
        payload=payload,
        checkpoint_id=request.POST.get("checkpoint_id") or None,
        actor=actor,
    )
