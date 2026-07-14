"""Runtime context for graph execution."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
import logging

from langgraph_automation.core.errors import MissingRuntimeDependencyError
from langgraph_automation.graphs.config import GraphRuntimeConfig
from langgraph_automation.graphs.inputs import GraphExecutionInput
from langgraph_automation.graphs.registry import GraphRegistry
from langgraph_automation.integrations.artifact.base import ArtifactStore
from langgraph_automation.integrations.checkpoint.base import CheckpointStore
from langgraph_automation.integrations.llm.base import LLMClient
from langgraph_automation.integrations.observability.base import EventSink
from langgraph_automation.integrations.observability.context import bind_observability_context
from langgraph_automation.integrations.observability.types import ObservabilityContext, SpanRef
from langgraph_automation.integrations.tools.base import ToolRegistry


@dataclass(slots=True)
class GraphRuntime:
    """Bundle execution-plane dependencies passed to graph runners and nodes."""

    logger: logging.Logger
    observability: ObservabilityContext = field(default_factory=ObservabilityContext)
    workflow_config: GraphRuntimeConfig = field(default_factory=GraphRuntimeConfig)
    graph_registry: GraphRegistry | None = None
    event_sink: EventSink | None = None
    llm_client: LLMClient | None = None
    tool_registry: ToolRegistry | None = None
    artifact_store: ArtifactStore | None = None
    checkpoint_store: CheckpointStore | None = None
    execution_input: GraphExecutionInput | None = None

    def require_llm_client(self) -> LLMClient:
        """Return the configured LLM client or fail fast."""

        if self.llm_client is None:
            raise MissingRuntimeDependencyError('LLM client is not configured for this runtime')
        return self.llm_client

    def require_tool_registry(self) -> ToolRegistry:
        """Return the configured tool registry or fail fast."""

        if self.tool_registry is None:
            raise MissingRuntimeDependencyError('Tool registry is not configured for this runtime')
        return self.tool_registry

    def require_graph_registry(self) -> GraphRegistry:
        """Return the configured graph registry or fail fast."""

        if self.graph_registry is None:
            raise MissingRuntimeDependencyError('Graph registry is not configured for this runtime')
        return self.graph_registry

    def require_execution_input(self) -> GraphExecutionInput:
        """Return the transient execution input or fail fast."""

        if self.execution_input is None:
            raise MissingRuntimeDependencyError('Execution input is not configured for this runtime')
        return self.execution_input

    def with_execution_input(self, execution_input: GraphExecutionInput | None) -> 'GraphRuntime':
        """Return a new runtime with updated transient execution input."""

        return replace(self, execution_input=execution_input)

    def with_parent_span(self, parent_span: SpanRef | None, node_name: str | None = None) -> 'GraphRuntime':
        """Return a new runtime with updated observability parent span context."""

        updated_observability = self.observability.with_parent_span(parent_span, node_name)
        return replace(
            self,
            observability=updated_observability,
            llm_client=bind_observability_context(self.llm_client, updated_observability),
            tool_registry=bind_observability_context(self.tool_registry, updated_observability),
            artifact_store=bind_observability_context(self.artifact_store, updated_observability),
            checkpoint_store=bind_observability_context(self.checkpoint_store, updated_observability),
        )
