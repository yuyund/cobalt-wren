"""Graph execution-plane runtime config types."""

from __future__ import annotations

from dataclasses import dataclass, field

from langgraph_automation.graphs.constants import DEFAULT_GRAPH_KIND


@dataclass(frozen=True, slots=True)
class GraphRuntimeGraphConfig:
    """Execution-plane graph selection config."""

    kind: str = DEFAULT_GRAPH_KIND


@dataclass(frozen=True, slots=True)
class GraphRuntimeLLMConfig:
    """Execution-plane LLM config."""

    enabled: bool = False
    model: str = ''
    temperature: float | None = None
    max_tokens: int | None = None


@dataclass(frozen=True, slots=True)
class GraphRuntimeToolConfig:
    """Execution-plane tool config."""

    allowed_tools: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class GraphRuntimeConfig:
    """Minimal config consumed by GraphRuntime and graph nodes."""

    graph: GraphRuntimeGraphConfig = field(default_factory=GraphRuntimeGraphConfig)
    llm: GraphRuntimeLLMConfig = field(default_factory=GraphRuntimeLLMConfig)
    tools: GraphRuntimeToolConfig = field(default_factory=GraphRuntimeToolConfig)
