from __future__ import annotations
import asyncio
from types import SimpleNamespace
import pytest
from cobalt_wren.apps.web.views import run_live

def test_async_stream_suppresses_unchanged_fragments_and_emits_heartbeat(monkeypatch: pytest.MonkeyPatch) -> None:
    live = SimpleNamespace(revision="same", terminal=False)
    async def load(_object_id: int):
        return live
    async def render(_live: object) -> str:
        return "<section>state</section>"
    monkeypatch.setattr(run_live, "_load_live", load)
    monkeypatch.setattr(run_live, "_render_live", render)
    monkeypatch.setattr(run_live, "_STREAM_INTERVAL_SECONDS", 0.0)
    monkeypatch.setattr(run_live, "_STREAM_HEARTBEAT_SECONDS", 0.0)
    monkeypatch.setattr(run_live, "_STREAM_MAX_ITERATIONS", 2)
    async def collect() -> list[bytes]:
        return [chunk async for chunk in run_live._stream_run_live(1)]
    chunks = asyncio.run(collect())
    assert sum(b"event: fragment" in chunk for chunk in chunks) == 1
    assert sum(b": heartbeat" in chunk for chunk in chunks) == 1

def test_async_stream_stops_cleanly_on_disconnect_cancellation(monkeypatch: pytest.MonkeyPatch) -> None:
    async def load(_object_id: int):
        raise asyncio.CancelledError
    monkeypatch.setattr(run_live, "_load_live", load)
    async def collect() -> list[bytes]:
        return [chunk async for chunk in run_live._stream_run_live(1)]
    assert asyncio.run(collect()) == []
