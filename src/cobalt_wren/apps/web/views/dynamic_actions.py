"""Dynamic action views for allowlisted UI actions."""

from __future__ import annotations

from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    HttpResponseNotAllowed,
    HttpResponseNotFound,
)
from django.shortcuts import render

from cobalt_wren.apps.automation.models import Run
from cobalt_wren.apps.automation.services.audit import record_operation
from cobalt_wren.apps.web.access import actor_allowed, run_action_permission

from cobalt_wren.apps.automation.ui.actions import dispatch_ui_action
from cobalt_wren.apps.automation.ui.builders import build_detail_page_spec


def dynamic_action_view(
    request: HttpRequest, model_key: str, object_id: int, action_name: str
) -> HttpResponse:
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    permission = run_action_permission(action_name)
    if not actor_allowed(request, permission):
        record_operation(
            actor=getattr(request, "user", None),
            action=action_name,
            target_type=model_key,
            target_id=object_id,
            outcome="denied",
            payload=dict(request.POST),
        )
        return HttpResponseForbidden("Forbidden")
    try:
        dispatch_ui_action(
            model_key,
            object_id,
            action_name,
            getattr(request, "user", None),
            request=request,
        )
        run = Run.objects.filter(pk=object_id).first() if model_key == "runs" else None
        record_operation(
            actor=getattr(request, "user", None),
            action=action_name,
            target_type=model_key,
            target_id=object_id,
            outcome="succeeded",
            run=run,
            payload=dict(request.POST),
        )
    except LookupError:
        return HttpResponseNotFound("Not found")
    except PermissionError:
        return HttpResponseForbidden("Forbidden")
    except ValueError as exc:
        return HttpResponseBadRequest(str(exc))
    page = build_detail_page_spec(
        model_key, object_id, actor=getattr(request, "user", None)
    )
    return render(request, "dynamic/detail.html", {"page": page})
