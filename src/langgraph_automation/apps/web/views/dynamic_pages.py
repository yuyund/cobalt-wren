'''Dynamic page views for list, detail, and form pages.'''

from __future__ import annotations

from django.http import HttpRequest, HttpResponse, HttpResponseNotFound
from django.shortcuts import render

from langgraph_automation.apps.automation.ui.builders import build_detail_page_spec, build_form_spec, build_list_page_spec


def dynamic_list_view(request: HttpRequest, model_key: str) -> HttpResponse:
    try:
        page = build_list_page_spec(model_key, actor=getattr(request, 'user', None))
    except LookupError:
        return HttpResponseNotFound('Not found')
    return render(request, 'dynamic/list.html', {'page': page})


def dynamic_detail_view(request: HttpRequest, model_key: str, object_id: int) -> HttpResponse:
    try:
        page = build_detail_page_spec(model_key, object_id, actor=getattr(request, 'user', None))
    except LookupError:
        return HttpResponseNotFound('Not found')
    return render(request, 'dynamic/detail.html', {'page': page})


def dynamic_form_view(request: HttpRequest, model_key: str, object_id: int | None = None) -> HttpResponse:
    try:
        page = build_form_spec(model_key, object_id, actor=getattr(request, 'user', None))
    except LookupError:
        return HttpResponseNotFound('Not found')
    return render(request, 'dynamic/form.html', {'page': page})
