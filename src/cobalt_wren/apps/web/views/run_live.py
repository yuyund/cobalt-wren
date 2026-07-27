"""Live Run HTML fragment and asynchronous server-sent-event views."""
from __future__ import annotations
import asyncio
from collections.abc import AsyncIterator
import json
from asgiref.sync import sync_to_async
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden, HttpResponseNotFound, StreamingHttpResponse
from django.http.response import HttpResponseBase
from django.shortcuts import render
from django.template.loader import render_to_string
from cobalt_wren.apps.automation.ui.run_live import RunLiveSpec, build_run_live_spec
from cobalt_wren.apps.web.access import actor_allowed
from cobalt_wren.apps.web.presentation.run_components import get_run_live_components

_STREAM_INTERVAL_SECONDS = 2.0
_STREAM_HEARTBEAT_SECONDS = 15.0
_STREAM_MAX_ITERATIONS = 900


def _authorize(request: HttpRequest) -> HttpResponse | None:
    if actor_allowed(request, "automation.view_run"):
        return None
    return HttpResponseForbidden("Forbidden")


def _live_context(live: RunLiveSpec) -> dict[str, object]:
    return {"live": live, "components": get_run_live_components()}


def run_live_view(request: HttpRequest, object_id: int) -> HttpResponse:
    denied = _authorize(request)
    if denied is not None:
        return denied
    try:
        live = build_run_live_spec(object_id, actor=getattr(request, "user", None))
    except LookupError:
        return HttpResponseNotFound("Not found")
    return render(request, "dynamic/run_live.html", _live_context(live))


async def _load_live(object_id: int) -> RunLiveSpec:
    return await sync_to_async(build_run_live_spec, thread_sensitive=True)(object_id)


async def _render_live(live: RunLiveSpec) -> str:
    return await sync_to_async(render_to_string, thread_sensitive=True)("dynamic/run_live.html", _live_context(live))


async def _stream_run_live(object_id: int) -> AsyncIterator[bytes]:
    last_revision = ""
    heartbeat_elapsed = _STREAM_HEARTBEAT_SECONDS
    try:
        for sequence in range(_STREAM_MAX_ITERATIONS):
            try:
                live = await _load_live(object_id)
            except LookupError:
                yield b"event: unavailable\ndata: {}\n\n"
                return
            if live.revision != last_revision:
                html = await _render_live(live)
                payload = json.dumps({"html": html, "revision": live.revision, "terminal": live.terminal}, ensure_ascii=False)
                yield f"id: {sequence}\nevent: fragment\ndata: {payload}\n\n".encode()
                last_revision = live.revision
                heartbeat_elapsed = 0.0
            elif heartbeat_elapsed >= _STREAM_HEARTBEAT_SECONDS:
                yield b": heartbeat\n\n"
                heartbeat_elapsed = 0.0
            if live.terminal:
                return
            await asyncio.sleep(_STREAM_INTERVAL_SECONDS)
            heartbeat_elapsed += _STREAM_INTERVAL_SECONDS
    except asyncio.CancelledError:
        return


async def run_live_stream_view(request: HttpRequest, object_id: int) -> HttpResponseBase:
    allowed = await sync_to_async(actor_allowed, thread_sensitive=True)(request, "automation.view_run")
    if not allowed:
        return HttpResponseForbidden("Forbidden")
    try:
        await _load_live(object_id)
    except LookupError:
        return HttpResponseNotFound("Not found")
    if not hasattr(request, "scope"):
        fallback = HttpResponse("SSE requires ASGI", status=503, content_type="text/plain; charset=utf-8")
        fallback["Cache-Control"] = "no-store"
        return fallback
    stream = StreamingHttpResponse(_stream_run_live(object_id), content_type="text/event-stream; charset=utf-8")
    stream["Cache-Control"] = "no-cache, no-transform"
    stream["X-Accel-Buffering"] = "no"
    return stream
