'''Tool integration interfaces and normalized result types.'''

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(slots=True, frozen=True)
class ToolResult:
    '''Normalized tool execution result.'''

    output: Any = None
    output_summary: str = ''
    exit_code: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    error_message: str = ''


@runtime_checkable
class ToolCallable(Protocol):
    def __call__(self, **kwargs: Any) -> ToolResult: ...


@runtime_checkable
class ToolRegistry(Protocol):
    def register(self, name: str, tool: ToolCallable) -> None: ...
    def get(self, name: str) -> ToolCallable: ...
    def run(self, name: str, **kwargs: Any) -> ToolResult: ...
