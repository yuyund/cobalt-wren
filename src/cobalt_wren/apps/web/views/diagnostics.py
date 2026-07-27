"""Authorized, audited diagnostic detail fragments."""
from __future__ import annotations
from django.http import HttpRequest, HttpResponse, HttpResponseNotFound
from django.shortcuts import render
from cobalt_wren.apps.automation.services.audit import record_operation
from cobalt_wren.apps.automation.ui.diagnostics import diagnostic_permission, resolve_diagnostic_detail
from cobalt_wren.apps.automation.ui.registry import get_model_ui_config
from cobalt_wren.apps.web.access import actor_allowed

def diagnostic_detail_view(request: HttpRequest, model_key: str, object_id: int, field_name: str) -> HttpResponse:
    actor = getattr(request, "user", None)
    if not actor_allowed(request, diagnostic_permission(model_key)):
        record_operation(actor=actor, action="diagnostic.inspect", target_type=model_key, target_id=object_id, outcome="denied", payload={"field": field_name})
        return HttpResponse(status=403)
    config = get_model_ui_config(model_key)
    obj = config.detail_selector(object_id, actor) if config is not None else None
    if obj is None:
        return HttpResponseNotFound("Diagnostic target not found")
    detail = resolve_diagnostic_detail(model_key, obj, field_name)
    if detail is None:
        return HttpResponseNotFound("Diagnostic detail unavailable")
    run = getattr(obj, "run", None)
    if model_key == "runs":
        run = obj
    record_operation(actor=actor, action="diagnostic.inspect", target_type=model_key, target_id=object_id, outcome="succeeded", run=run, payload={"field": field_name, "source": detail.source})
    return render(request, "dynamic/diagnostic_detail.html", {"detail": detail})
