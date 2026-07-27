"""Test doubles for tool registry wrappers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cobalt_wren.integrations.tools.base import ToolResult


@dataclass(slots=True)
class RecordingToolCallable:
    result: ToolResult | Any
    calls: list[dict[str, Any]] | None = None

    def __call__(self, **kwargs: Any) -> ToolResult | Any:
        if self.calls is not None:
            self.calls.append(dict(kwargs))
        return self.result


class FailingToolCallable:
    def __init__(self, exc: Exception | None = None) -> None:
        self.exc = exc or RuntimeError('tool failure')
        self.calls: list[dict[str, Any]] = []

    def __call__(self, **kwargs: Any) -> ToolResult:
        self.calls.append(dict(kwargs))
        raise self.exc
