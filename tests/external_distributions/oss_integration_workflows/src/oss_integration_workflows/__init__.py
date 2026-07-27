"""Separately installable LangGraph and LlamaIndex Workflows demo plugin."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from workflows import Workflow, step
from workflows.events import Event, StartEvent, StopEvent

from cobalt_wren.api.plugins import (
    PLUGIN_API_VERSION,
    Plugin,
    PluginContributions,
    PluginMetadata,
)
from cobalt_wren.api.workflow import (
    WorkflowBuildContext,
    WorkflowContribution,
    WorkflowDefinition,
    WorkflowMetadata,
    WorkflowRequirements,
)
from cobalt_wren.integrations.langgraph import integrate_langgraph
from cobalt_wren.integrations.llamaindex_workflows import (
    integrate_llamaindex_workflow,
)

LANGGRAPH_WORKFLOW_KIND = "external.oss.langgraph"
LLAMAINDEX_WORKFLOW_KIND = "external.oss.llamaindex"


class GraphState(TypedDict, total=False):
    message: str
    normalized: str
    result: dict[str, object]


def _normalize_graph(state: GraphState) -> GraphState:
    return {"normalized": state.get("message", "").strip().upper()}


def _finish_graph(state: GraphState) -> GraphState:
    return {
        "result": {
            "framework": "LangGraph",
            "message": state["normalized"],
        }
    }


def _build_langgraph(context: WorkflowBuildContext) -> object:
    del context
    graph = StateGraph(GraphState)
    graph.add_node("normalize", _normalize_graph)
    graph.add_node("finish", _finish_graph)
    graph.add_edge(START, "normalize")
    graph.add_edge("normalize", "finish")
    graph.add_edge("finish", END)
    return integrate_langgraph(
        graph.compile(
            name="external-oss-langgraph",
            checkpointer=InMemorySaver(),
        ),
        workflow_kind=LANGGRAPH_WORKFLOW_KIND,
        output_key="result",
    )


class Validated(Event):
    text: str


class ExternalLlamaIndexWorkflow(Workflow):
    @step
    async def prepare(self, event: StartEvent) -> Validated:
        return Validated(text=str(event.get("message", "")).strip())

    @step
    async def finish(self, event: Validated) -> StopEvent:
        return StopEvent(
            result={
                "framework": "LlamaIndex Workflows",
                "message": event.text.upper(),
            }
        )


def _build_llamaindex(context: WorkflowBuildContext) -> object:
    del context
    return integrate_llamaindex_workflow(
        ExternalLlamaIndexWorkflow(timeout=10),
        workflow_kind=LLAMAINDEX_WORKFLOW_KIND,
    )


def _contribution(
    *,
    kind: str,
    name: str,
    framework: str,
    build: Callable[[WorkflowBuildContext], object],
) -> WorkflowContribution:
    return WorkflowContribution(
        kind=kind,
        definition=WorkflowDefinition(
            kind=kind,
            metadata=WorkflowMetadata(
                name=name,
                version="1.0.0",
                tags=("external", "oss-integration", framework),
                metadata={"framework": framework},
            ),
            requirements=WorkflowRequirements(),
            build=build,
            input_schema={
                "type": "object",
                "properties": {
                    "message": {"type": "string", "title": "Message"},
                },
                "required": ["message"],
            },
        ),
    )


def create_plugin() -> Plugin:
    workflows = (
        _contribution(
            kind=LANGGRAPH_WORKFLOW_KIND,
            name="External LangGraph Demo",
            framework="langgraph",
            build=_build_langgraph,
        ),
        _contribution(
            kind=LLAMAINDEX_WORKFLOW_KIND,
            name="External LlamaIndex Workflows Demo",
            framework="llamaindex-workflows",
            build=_build_llamaindex,
        ),
    )
    return Plugin(
        metadata=PluginMetadata(
            name="oss-integration-workflows",
            version="1.0.0",
            description="Separately installed OSS workflow integration demos.",
            plugin_types=("workflow",),
            provides={
                "workflows": (
                    LANGGRAPH_WORKFLOW_KIND,
                    LLAMAINDEX_WORKFLOW_KIND,
                )
            },
            metadata={"plugin_api_version": PLUGIN_API_VERSION},
        ),
        contributions=PluginContributions(workflows=workflows),
    )


__all__ = [
    "LANGGRAPH_WORKFLOW_KIND",
    "LLAMAINDEX_WORKFLOW_KIND",
    "create_plugin",
]
