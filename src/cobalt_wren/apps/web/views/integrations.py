"""Workflow integration availability and health views."""

from __future__ import annotations

from django.contrib.auth.views import redirect_to_login
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden, HttpResponseNotFound
from django.shortcuts import render

from cobalt_wren.api.errors import PluginResolutionError
from cobalt_wren.apps.automation.ui.integration_health import (
    build_integration_health_detail,
    build_integration_health_list,
)
from cobalt_wren.apps.web.access import actor_allowed, require_login_enabled


def _guard(request: HttpRequest) -> HttpResponse | None:
    if actor_allowed(request, "automation.view_integrationhealth"):
        return None
    if require_login_enabled() and not bool(
        getattr(request.user, "is_authenticated", False)
    ):
        return redirect_to_login(request.get_full_path())
    return HttpResponseForbidden("Forbidden")


def integration_health_list_view(request: HttpRequest) -> HttpResponse:
    denied = _guard(request)
    if denied is not None:
        return denied
    return render(
        request,
        "integrations/list.html",
        {"page": build_integration_health_list()},
    )


def integration_health_detail_view(
    request: HttpRequest, integration_id: str
) -> HttpResponse:
    denied = _guard(request)
    if denied is not None:
        return denied
    try:
        integration = build_integration_health_detail(integration_id)
    except PluginResolutionError:
        return HttpResponseNotFound("Not found")
    return render(
        request,
        "integrations/detail.html",
        {"integration": integration},
    )
