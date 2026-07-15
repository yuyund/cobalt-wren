"""Workflow contribution definition for the llm_echo_summary reference workflow."""

from __future__ import annotations

from langgraph_automation.api.workflow import (
    WorkflowContribution,
    WorkflowDefinition,
    WorkflowMetadata,
    WorkflowRequirements,
)
from langgraph_automation.graphs.constants import LLM_ECHO_SUMMARY_GRAPH_KIND
from langgraph_automation.graphs.types import GraphDefinition

from .graph import build_llm_echo_summary_graph

REFERENCE_WORKFLOW_KIND = "reference.llm_echo_summary"


def build_llm_echo_summary_graph_definition() -> GraphDefinition:
    return GraphDefinition(
        kind=LLM_ECHO_SUMMARY_GRAPH_KIND,
        builder=build_llm_echo_summary_graph,
        requires_llm=True,
        required_tools=("echo",),
        description=(
            "Reference diagnostic workflow that verifies LLM, EchoTool, "
            "observability, and safe output wiring through GraphRuntime."
        ),
    )


def llm_echo_summary_workflow_contribution() -> WorkflowContribution:
    workflow_metadata = WorkflowMetadata(
        name="LLM Echo Summary",
        description="Reference diagnostic workflow for LLM echo and summary behavior.",
        version="0.1.0",
        tags=("reference", "diagnostic"),
        metadata={"graph_kind": LLM_ECHO_SUMMARY_GRAPH_KIND},
    )
    workflow_requirements = WorkflowRequirements(
        provider_profiles=("default",),
        tools=("echo",),
        artifact_store=False,
        checkpoint_store=False,
        event_sinks=(),
    )
    workflow_definition = WorkflowDefinition(
        kind=REFERENCE_WORKFLOW_KIND,
        metadata=workflow_metadata,
        requirements=workflow_requirements,
        build=build_llm_echo_summary_graph_definition,
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        extra={"graph_kind": LLM_ECHO_SUMMARY_GRAPH_KIND},
    )

    return WorkflowContribution(
        kind=REFERENCE_WORKFLOW_KIND,
        definition=workflow_definition,
        metadata={"graph_kind": LLM_ECHO_SUMMARY_GRAPH_KIND},
    )


LLM_ECHO_SUMMARY_GRAPH_DEFINITION = build_llm_echo_summary_graph_definition()
LLM_ECHO_SUMMARY_WORKFLOW_CONTRIBUTION = llm_echo_summary_workflow_contribution()
