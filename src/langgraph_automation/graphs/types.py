"""Pure graph selection metadata types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class GraphRuntimeRequirements:
    """Pure dependency metadata for a graph kind."""

    requires_llm: bool = False
    required_tools: tuple[str, ...] = ()


@dataclass(frozen=True)
class GraphDefinition:
    """Registry entry for a concrete graph builder."""

    kind: str
    builder: Callable[..., Any]
    requires_llm: bool = False
    required_tools: tuple[str, ...] = ()
    description: str = ''

    @property
    def requirements(self) -> GraphRuntimeRequirements:
        return GraphRuntimeRequirements(requires_llm=self.requires_llm, required_tools=self.required_tools)
