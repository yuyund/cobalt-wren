'''Dynamic page views for list, detail, and form pages.'''
from __future__ import annotations

from django.contrib.auth.views import redirect_to_login
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden, HttpResponseNotFound
from django.shortcuts import render

from cobalt_wren.apps.automation.ui.builders import build_detail_page_spec, build_form_spec, build_list_page_spec
from cobalt_wren.apps.automation.ui.detail_presentations import build_detail_presentation
from cobalt_wren.apps.automation.ui.run_live import build_run_live_spec
from cobalt_wren.apps.web.presentation.run_components import get_run_live_components
from cobalt_wren.apps.web.access import actor_allowed, require_login_enabled


def _guard(request: HttpRequest, permission: str) -> HttpResponse | None:
    if actor_allowed(request, permission):
        return None
    if require_login_enabled() and not bool(getattr(request.user, "is_authenticated", False)):
        return redirect_to_login(request.get_full_path())
    return HttpResponseForbidden("Forbidden")


def dynamic_list_view(request: HttpRequest, model_key: str) -> HttpResponse:
    denied = _guard(request, f"automation.view_{model_key.rstrip('s')}")
    if denied is not None:
        return denied
    try:
        page = build_list_page_spec(model_key, actor=getattr(request, 'user', None))
    except LookupError:
        return HttpResponseNotFound('Not found')
    return render(request, 'dynamic/list.html', {'page': page})


def dynamic_detail_view(request: HttpRequest, model_key: str, object_id: int) -> HttpResponse:
    denied = _guard(request, f"automation.view_{model_key.rstrip('s')}")
    if denied is not None:
        return denied
    try:
        page = build_detail_page_spec(model_key, object_id, actor=getattr(request, 'user', None))
    except LookupError:
        return HttpResponseNotFound('Not found')
    context: dict[str, object] = {'page': page, 'detail_presentation': build_detail_presentation(page)}
    if model_key == 'runs':
        context['live'] = build_run_live_spec(object_id, actor=getattr(request, 'user', None))
        context['components'] = get_run_live_components()
    return render(request, 'dynamic/detail.html', context)


def dynamic_form_view(request: HttpRequest, model_key: str, object_id: int | None = None) -> HttpResponse:
    denied = _guard(request, f"automation.change_{model_key.rstrip('s')}")
    if denied is not None:
        return denied
    try:
        page = build_form_spec(model_key, object_id, actor=getattr(request, 'user', None))
    except LookupError:
        return HttpResponseNotFound('Not found')
    return render(request, 'dynamic/form.html', {'page': page})
