"""Artifact preview and download views."""
from __future__ import annotations

from pathlib import Path

from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest, HttpResponseNotFound
from django.shortcuts import render

from langgraph_automation.apps.automation.services.audit import record_operation
from langgraph_automation.apps.web.access import actor_allowed

from langgraph_automation.apps.automation.services.artifact_access import load_artifact_body, preview_artifact_body


def artifact_preview_view(request: HttpRequest, object_id: int) -> HttpResponse:
    if not actor_allowed(request, "automation.view_artifact"):
        record_operation(actor=getattr(request, "user", None), action="artifact.preview", target_type="artifact", target_id=object_id, outcome="denied")
        return HttpResponse(status=403)
    try:
        artifact, text, content_type = preview_artifact_body(object_id)
    except LookupError:
        return HttpResponseNotFound("Artifact body not found")
    except (UnicodeDecodeError, ValueError):
        return HttpResponseBadRequest("Artifact cannot be previewed safely")
    record_operation(actor=getattr(request, "user", None), action="artifact.preview", target_type="artifact", target_id=object_id, outcome="succeeded", run=artifact.run)
    return render(request, "dynamic/artifact_preview.html", {"artifact": artifact, "preview": text, "content_type": content_type})


def artifact_download_view(request: HttpRequest, object_id: int) -> HttpResponse:
    if not actor_allowed(request, "automation.view_artifact"):
        record_operation(actor=getattr(request, "user", None), action="artifact.download", target_type="artifact", target_id=object_id, outcome="denied")
        return HttpResponse(status=403)
    try:
        loaded = load_artifact_body(object_id)
    except LookupError:
        return HttpResponseNotFound("Artifact body not found")
    except ValueError:
        return HttpResponseBadRequest("Artifact identity mismatch")
    filename = Path(loaded.artifact.storage_key).name or f"artifact-{object_id}"
    record_operation(actor=getattr(request, "user", None), action="artifact.download", target_type="artifact", target_id=object_id, outcome="succeeded", run=loaded.artifact.run)
    response = HttpResponse(loaded.body, content_type=loaded.content_type)
    response["Content-Disposition"] = f'attachment; filename="{filename.replace(chr(34), "")}"'
    response["X-Content-Type-Options"] = "nosniff"
    return response
