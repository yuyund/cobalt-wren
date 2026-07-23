"""SearXNG-compatible search tool."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from typing import Any

from langgraph_automation.integrations.tools.base import ToolResult

Transport = Callable[[Request, float], bytes]


def _default_transport(request: Request, timeout: float) -> bytes:
    with urlopen(request, timeout=timeout) as response:  # noqa: S310
        return response.read()


@dataclass(slots=True)
class SearXNGSearchTool:
    base_url: str
    timeout_seconds: float = 10.0
    max_results: int = 8
    transport: Transport = _default_transport

    def __call__(self, **kwargs: Any) -> ToolResult:
        query = kwargs.get("query")
        if not isinstance(query, str):
            return ToolResult(exit_code=2, error_message="search query is required")
        language = str(kwargs.get("language", "auto"))
        categories = str(kwargs.get("categories", "general"))
        time_range_value = kwargs.get("time_range")
        time_range = None if time_range_value is None else str(time_range_value)
        limit_value = kwargs.get("limit")
        limit = limit_value if isinstance(limit_value, int) and not isinstance(limit_value, bool) else None
        normalized_query = query.strip()
        if not normalized_query:
            return ToolResult(exit_code=2, error_message="search query is required")
        result_limit = min(max(1, int(limit or self.max_results)), self.max_results)
        params = {
            "q": normalized_query,
            "format": "json",
            "language": language,
            "categories": categories,
        }
        if time_range:
            params["time_range"] = time_range
        request = Request(
            f"{self.base_url.rstrip('/')}/search?{urlencode(params)}",
            headers={"Accept": "application/json", "User-Agent": "opportunity-research-workflow/0.1"},
        )
        try:
            payload = json.loads(self.transport(request, self.timeout_seconds).decode("utf-8"))
        except Exception:
            return ToolResult(exit_code=1, error_message="search backend request failed")
        raw_results = payload.get("results", []) if isinstance(payload, Mapping) else []
        results: list[dict[str, object]] = []
        for item in raw_results:
            if not isinstance(item, Mapping):
                continue
            url = str(item.get("url", "")).strip()
            title = str(item.get("title", "")).strip()
            if not url or not title:
                continue
            results.append(
                {
                    "title": title,
                    "url": url,
                    "snippet": str(item.get("content", item.get("snippet", ""))).strip(),
                    "engine": str(item.get("engine", "")),
                    "score": float(item.get("score", 0.0) or 0.0),
                }
            )
            if len(results) >= result_limit:
                break
        return ToolResult(
            output=results,
            output_summary=f"{len(results)} search results",
            metadata={"query": normalized_query, "result_count": len(results)},
        )
