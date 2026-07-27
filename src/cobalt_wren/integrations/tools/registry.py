'''Tool registry integration.'''

from __future__ import annotations

from typing import Any

from .base import ToolCallable, ToolRegistry, ToolResult


class InMemoryToolRegistry(ToolRegistry):
    def __init__(self) -> None:
        self._tools: dict[str, ToolCallable] = {}

    def register(self, name: str, tool: ToolCallable) -> None:
        self._tools[name] = tool

    def get(self, name: str) -> ToolCallable:
        return self._tools[name]

    def run(self, name: str, **kwargs: Any) -> ToolResult:
        tool = self.get(name)
        result = tool(**kwargs)
        if isinstance(result, ToolResult):
            return result
        return ToolResult(output=result, output_summary=str(result), metadata={'tool_name': name})
