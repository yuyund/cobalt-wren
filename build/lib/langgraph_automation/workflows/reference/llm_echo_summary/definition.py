"""Workflow contribution definition for the llm_echo_summary reference workflow."""
from __future__ import annotations

from collections.abc import Iterable
from typing import cast

from langgraph_automation.api.workflow import WorkflowBuildContext, WorkflowContribution, WorkflowDefinition, WorkflowMetadata, WorkflowRequirements
from langgraph_automation.integrations.llm.base import LLMClient
from langgraph_automation.integrations.tools.base import ToolCallable

from .executable import LlmEchoSummaryExecutable

REFERENCE_WORKFLOW_KIND = "reference.llm_echo_summary"


def build_llm_echo_summary_executable(context: WorkflowBuildContext) -> LlmEchoSummaryExecutable:
    allowed = context.config.get("allowed_tools", ("echo",))
    if isinstance(allowed, str):
        allowed = (allowed,)
    if not isinstance(allowed, Iterable):
        raise TypeError("allowed_tools must be an iterable of tool names")
    return LlmEchoSummaryExecutable(
        llm_client=cast(LLMClient, context.require_provider("default")),
        echo_tool=cast(ToolCallable, context.require_tool("echo")),
        allowed_tools=tuple(str(item) for item in allowed),
    )


def llm_echo_summary_workflow_contribution() -> WorkflowContribution:
    definition = WorkflowDefinition(
        kind=REFERENCE_WORKFLOW_KIND,
        metadata=WorkflowMetadata(
            name="LLM Echo Summary",
            description="Reference diagnostic workflow for LLM echo and summary behavior.",
            version="0.1.0",
            tags=("reference", "diagnostic"),
        ),
        requirements=WorkflowRequirements(provider_profiles=("default",), tools=("echo",)),
        build=build_llm_echo_summary_executable,
        input_schema={"type": "object"},
        output_schema={"type": "object"},
    )
    return WorkflowContribution(kind=REFERENCE_WORKFLOW_KIND, definition=definition)


LLM_ECHO_SUMMARY_WORKFLOW_CONTRIBUTION = llm_echo_summary_workflow_contribution()
