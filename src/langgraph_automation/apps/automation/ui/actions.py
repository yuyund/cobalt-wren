'''Action specifications and dispatch for dynamic UI pages.'''

from __future__ import annotations

from django.http import HttpRequest

from langgraph_automation.apps.automation.ui.registry import get_model_ui_config
from langgraph_automation.apps.automation.ui.specs import ActionSpec
from langgraph_automation.apps.automation.models.artifact import Artifact
from langgraph_automation.apps.automation.models.run import Run
from langgraph_automation.apps.automation.ui.workflow_projection import build_resume_action_specs, dispatch_resume_action


def _resolve_action_url(model_key: str, object_id: int, action_name: str) -> str:
    return f'/ui/{model_key}/{object_id}/actions/{action_name}/'


def build_action_specs(model_key: str, obj: object | None, actor: object | None = None) -> list[ActionSpec]:
    config = get_model_ui_config(model_key)
    if config is None or obj is None:
        return []
    specs: list[ActionSpec] = []
    for action_config in config.actions:
        policy = action_config.policy(actor, obj) if action_config.policy is not None else None
        enabled = policy.allowed if policy is not None else True
        disabled_reason = policy.reason if policy is not None and not policy.allowed else None
        specs.append(
            ActionSpec(
                name=action_config.name,
                label=action_config.label,
                url=_resolve_action_url(model_key, int(getattr(obj, 'pk')), action_config.name),
                method=action_config.method,
                enabled=enabled,
                visible=True,
                danger=action_config.danger,
                confirm=action_config.confirm,
                hx_target='#page-root',
                disabled_reason=disabled_reason,
            )
        )
    if model_key == "runs" and isinstance(obj, Run):
        specs.extend(build_resume_action_specs(obj, actor=actor))
    if model_key == "artifacts" and isinstance(obj, Artifact):
        specs.extend([
            ActionSpec(name="preview", label="Preview", url=f"/ui/artifacts/{obj.pk}/preview/", method="GET"),
            ActionSpec(name="download", label="Download", url=f"/ui/artifacts/{obj.pk}/download/", method="GET"),
        ])
    return specs


def dispatch_ui_action(model_key: str, object_id: int, action_name: str, actor: object | None, request: HttpRequest | None = None) -> object:
    config = get_model_ui_config(model_key)
    if config is None:
        raise LookupError(f'Model {model_key!r} is not registered for UI rendering')
    obj = config.detail_selector(object_id, actor)
    if obj is None:
        raise LookupError(f'Object {model_key!r}:{object_id!r} was not found')
    if model_key == "runs" and action_name.startswith("resume-"):
        if request is None or not isinstance(obj, Run):
            raise LookupError("Resume request is unavailable")
        return dispatch_resume_action(obj, action_name.removeprefix("resume-"), request, actor=actor)
    action_config = next((action for action in config.actions if action.name == action_name), None)
    if action_config is None:
        raise LookupError(f'Action {action_name!r} is not registered for {model_key!r}')
    if action_config.policy is not None:
        policy = action_config.policy(actor, obj)
        if not policy.allowed:
            raise PermissionError(policy.reason)
    return action_config.handler(actor, object_id, request, obj)
