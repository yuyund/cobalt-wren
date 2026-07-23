"""Tests for the public reference workflow contribution."""
from langgraph_automation.workflows.reference.llm_echo_summary.definition import (
    LLM_ECHO_SUMMARY_WORKFLOW_CONTRIBUTION,
    REFERENCE_WORKFLOW_KIND,
    build_llm_echo_summary_executable,
    llm_echo_summary_workflow_contribution,
)
from langgraph_automation.workflows.reference.llm_echo_summary.executable import (
    LlmEchoSummaryExecutable,
)


def test_llm_echo_summary_contribution_shape() -> None:
    contribution = llm_echo_summary_workflow_contribution()
    assert contribution.kind == REFERENCE_WORKFLOW_KIND
    assert contribution.definition.kind == REFERENCE_WORKFLOW_KIND
    assert contribution.definition.metadata.name == "LLM Echo Summary"
    assert contribution.definition.requirements.provider_profiles == ("default",)
    assert contribution.definition.requirements.tools == ("echo",)
    assert contribution.definition.build is build_llm_echo_summary_executable


def test_llm_echo_summary_module_constant_matches_factory() -> None:
    assert LLM_ECHO_SUMMARY_WORKFLOW_CONTRIBUTION.kind == REFERENCE_WORKFLOW_KIND


def test_builder_returns_public_executable() -> None:
    from langgraph_automation.api.workflow import WorkflowBuildContext
    from tests.support.llm_doubles import RecordingLLMClient
    from langgraph_automation.integrations.tools.safe_tools import EchoTool

    executable = build_llm_echo_summary_executable(
        WorkflowBuildContext(
            workflow_kind=REFERENCE_WORKFLOW_KIND,
            providers={"default": RecordingLLMClient()},
            tools={"echo": EchoTool()},
        )
    )
    assert isinstance(executable, LlmEchoSummaryExecutable)
