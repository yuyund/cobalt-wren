"""Framework-neutral integration action projection and dispatch."""

from __future__ import annotations

from collections.abc import Mapping

from django.http import HttpRequest
from django.utils import timezone

from cobalt_wren.apps.automation.models.integration_projection import (
    IntegrationProjectionRecord,
)
from cobalt_wren.apps.automation.models.run import Run
from cobalt_wren.apps.automation.policies.runs import can_resume_run
from cobalt_wren.apps.automation.services import runtime as runtime_module
from cobalt_wren.apps.automation.services.dispatch import dispatch_resume
from cobalt_wren.apps.automation.services.workflow_reference import (
    parse_workflow_reference,
)
from cobalt_wren.apps.automation.ui.specs import ActionSpec, FieldSpec

_ACTION_SCHEMA_ID = "integration.actions.v1"
_MAX_ACTIONS = 10
_MAX_FIELDS = 20
_SUPPORTED_TYPES = {"string", "integer", "number", "boolean"}


def _active_action_records(run: Run):
    return IntegrationProjectionRecord.objects.filter(
        run=run,
        schema_id=_ACTION_SCHEMA_ID,
        expires_at__gt=timezone.now(),
    ).order_by("created_at")


def _actions(record: IntegrationProjectionRecord) -> list[Mapping[str, object]]:
    raw = record.payload.get("actions") if isinstance(record.payload, Mapping) else None
    if not isinstance(raw, list):
        return []
    return [item for item in raw[:_MAX_ACTIONS] if isinstance(item, Mapping)]


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
        fields.append(
            FieldSpec(
                name=name,
                label=str(raw.get("title") or name.replace("_", " ").title()),
                raw_value=None,
                display_value="",
                field_type=field_type,
                component=(
                    "textarea"
                    if raw.get("format") == "textarea"
                    else ("select" if choices else "input")
                ),
                readonly=False,
                required=name in required,
                help_text=str(raw.get("description")) if raw.get("description") else None,
                choices=choices,
            )
        )
    return fields


def _descriptor_id(record_id: int, action_id: str) -> str:
    return f"integration-{record_id}-{action_id}"


def build_integration_action_specs(
    run: Run, actor: object | None = None
) -> list[ActionSpec]:
    policy = can_resume_run(actor, run)
    if not policy.allowed:
        return []
    specs: list[ActionSpec] = []
    for record in _active_action_records(run):
        for action in _actions(record):
            action_id = str(action.get("action_id", "")).strip()
            if not action_id or str(action.get("target_kind", "run")) != "run":
                continue
            available = bool(action.get("available", True))
            descriptor_name = _descriptor_id(record.pk, action_id)
            specs.append(
                ActionSpec(
                    name=descriptor_name,
                    label=str(action.get("label") or action_id.replace("_", " ").title()),
                    url=f"/ui/runs/{run.pk}/actions/{descriptor_name}/",
                    method="POST",
                    enabled=available,
                    danger=str(action.get("safety", "mutating")) == "destructive",
                    confirm=str(action.get("confirm")) if action.get("confirm") else None,
                    hx_target="#page-root",
                    disabled_reason=(
                        str(action.get("unavailable_reason", "")) or None
                        if not available
                        else None
                    ),
                    input_fields=_schema_fields(action.get("input_schema")),
                    hidden_fields={
                        "integration_action_record": str(record.pk),
                        "integration_action_id": action_id,
                    },
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


def _prepared(run: Run):
    reference = parse_workflow_reference(run.workflow.definition_payload)
    if reference is None:
        raise LookupError("Workflow reference is unavailable")
    return runtime_module.get_run_execution_services().prepare_workflow(reference)


def dispatch_integration_action(
    run: Run,
    action_name: str,
    request: HttpRequest,
    *,
    actor: object | None = None,
) -> object:
    policy = can_resume_run(actor, run)
    if not policy.allowed:
        raise PermissionError(policy.reason)
    prefix = "integration-"
    if not action_name.startswith(prefix):
        raise LookupError("Integration action is unavailable")
    remainder = action_name.removeprefix(prefix)
    record_text, separator, action_id = remainder.partition("-")
    if not separator or not record_text.isdigit() or not action_id:
        raise LookupError("Integration action identity is invalid")
    record = _active_action_records(run).filter(pk=int(record_text)).first()
    if record is None:
        raise PermissionError("Integration action is no longer available")
    descriptor = next(
        (
            item
            for item in _actions(record)
            if str(item.get("action_id", "")) == action_id
        ),
        None,
    )
    if descriptor is None:
        raise LookupError("Integration action descriptor is unavailable")
    if not bool(descriptor.get("available", True)):
        raise PermissionError(str(descriptor.get("unavailable_reason", "Action unavailable")))
    if action_id != "resume":
        raise LookupError("Integration action is not supported by the current router")
    prepared = _prepared(run)
    if not callable(getattr(prepared.executable, "resume", None)):
        raise PermissionError("Prepared workflow no longer supports resume")
    fields = _schema_fields(descriptor.get("input_schema"))
    raw_payload = descriptor.get("payload", {})
    payload = dict(raw_payload) if isinstance(raw_payload, Mapping) else {}
    for field in fields:
        raw = request.POST.get(field.name, "")
        if field.required and not raw.strip():
            raise ValueError(f"{field.label} is required")
        if raw or field.field_type == "boolean":
            payload[field.name] = _coerce(field, raw)
    metadata = descriptor.get("metadata")
    checkpoint_id = (
        str(metadata.get("checkpoint_id"))
        if isinstance(metadata, Mapping) and metadata.get("checkpoint_id")
        else None
    )
    return dispatch_resume(
        run=run,
        payload=payload,
        checkpoint_id=checkpoint_id,
        actor=actor,
    )


__all__ = ["build_integration_action_specs", "dispatch_integration_action"]
