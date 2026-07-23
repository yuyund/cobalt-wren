from __future__ import annotations

import json
from pathlib import Path
import sys
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).parents[3]
EXAMPLE_SRC = ROOT / "packages" / "opportunity_research_workflow" / "src"
sys.path.insert(0, str(EXAMPLE_SRC))

from opportunity_research_workflow import SearXNGSearchTool  # noqa: E402


def test_searxng_tool_builds_json_request_and_normalizes_results() -> None:
    observed: dict[str, object] = {}

    def transport(request, timeout: float) -> bytes:
        observed["url"] = request.full_url
        observed["timeout"] = timeout
        return json.dumps(
            {
                "results": [
                    {
                        "title": "Market evidence",
                        "url": "https://example.test/evidence",
                        "content": "Customer pain",
                        "engine": "test",
                        "score": 1.2,
                    }
                ]
            }
        ).encode()

    tool = SearXNGSearchTool(
        base_url="http://searxng.test",
        timeout_seconds=3.0,
        max_results=5,
        transport=transport,
    )
    result = tool(query="revenue opportunity", language="en", limit=2)

    assert result.exit_code == 0
    assert result.output[0]["title"] == "Market evidence"
    parsed = urlparse(str(observed["url"]))
    assert parse_qs(parsed.query)["q"] == ["revenue opportunity"]
    assert parse_qs(parsed.query)["format"] == ["json"]
    assert observed["timeout"] == 3.0


def test_searxng_tool_returns_safe_failure_without_backend_details() -> None:
    def transport(_request, _timeout: float) -> bytes:
        raise OSError("private network detail")

    result = SearXNGSearchTool(
        base_url="http://searxng.test",
        transport=transport,
    )(query="market")

    assert result.exit_code == 1
    assert result.error_message == "search backend request failed"
    assert "private" not in result.error_message
