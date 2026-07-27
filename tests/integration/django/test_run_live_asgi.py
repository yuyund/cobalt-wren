from __future__ import annotations
from asgiref.sync import async_to_sync
from asgiref.testing import ApplicationCommunicator
import pytest
from cobalt_wren.apps.automation.models import Run, Workflow
from cobalt_wren.apps.automation.models.run import RunStatus
from cobalt_wren.config.asgi import application

@pytest.mark.django_db(transaction=True)
def test_run_live_stream_uses_asgi_async_streaming_response() -> None:
    workflow = Workflow.objects.create(name="asgi-stream-workflow")
    run = Run.objects.create(workflow=workflow, name="asgi-stream-run", status=RunStatus.SUCCEEDED)

    async def request() -> tuple[dict[str, object], bytes]:
        communicator = ApplicationCommunicator(
            application,
            {
                "type": "http",
                "asgi": {"version": "3.0", "spec_version": "2.3"},
                "http_version": "1.1",
                "method": "GET",
                "scheme": "http",
                "path": f"/ui/runs/{run.pk}/stream/",
                "raw_path": f"/ui/runs/{run.pk}/stream/".encode(),
                "query_string": b"",
                "root_path": "",
                "headers": [(b"host", b"testserver")],
                "client": ("127.0.0.1", 12345),
                "server": ("testserver", 80),
            },
        )
        await communicator.send_input({"type": "http.request", "body": b"", "more_body": False})
        start = await communicator.receive_output(timeout=2)
        chunks: list[bytes] = []
        while True:
            message = await communicator.receive_output(timeout=2)
            assert message["type"] == "http.response.body"
            chunks.append(message.get("body", b""))
            if not message.get("more_body", False):
                break
        await communicator.wait(timeout=2)
        return start, b"".join(chunks)

    start, body = async_to_sync(request)()
    headers = {name.lower(): value for name, value in start["headers"]}
    assert start["type"] == "http.response.start"
    assert start["status"] == 200
    assert headers[b"content-type"].startswith(b"text/event-stream")
    assert headers[b"x-accel-buffering"] == b"no"
    assert b"event: fragment" in body
    assert b'"terminal": true' in body
