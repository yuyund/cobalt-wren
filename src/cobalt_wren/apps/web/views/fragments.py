'''HTMX fragment views.''' 

from __future__ import annotations

from django.http import HttpRequest, HttpResponse, HttpResponseNotFound
from django.shortcuts import render

from cobalt_wren.apps.automation.ui.builders import build_fragment_spec


def dynamic_fragment_view(request: HttpRequest, model_key: str, object_id: int, fragment_name: str) -> HttpResponse:
    try:
        section = build_fragment_spec(model_key, object_id, fragment_name, actor=getattr(request, 'user', None))
    except LookupError:
        return HttpResponseNotFound('Not found')
    return render(request, 'dynamic/fragment.html', {'section': section})
