'''Dynamic action views for allowlisted UI actions.'''

from __future__ import annotations

from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, HttpResponseNotAllowed, HttpResponseNotFound
from django.shortcuts import render

from langgraph_automation.apps.automation.ui.actions import dispatch_ui_action
from langgraph_automation.apps.automation.ui.builders import build_detail_page_spec


def dynamic_action_view(request: HttpRequest, model_key: str, object_id: int, action_name: str) -> HttpResponse:
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    try:
        dispatch_ui_action(model_key, object_id, action_name, getattr(request, 'user', None), request=request)
    except LookupError:
        return HttpResponseNotFound('Not found')
    except PermissionError:
        return HttpResponseForbidden('Forbidden')
    except ValueError as exc:
        return HttpResponseBadRequest(str(exc))
    page = build_detail_page_spec(model_key, object_id, actor=getattr(request, 'user', None))
    return render(request, 'dynamic/detail.html', {'page': page})
