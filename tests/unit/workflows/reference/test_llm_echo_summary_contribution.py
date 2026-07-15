"""Tests for the llm_echo_summary reference workflow contribution."""

from __future__ import annotations

from langgraph_automation.workflows.reference.llm_echo_summary.definition import (
    LLM_ECHO_SUMMARY_WORKFLOW_CONTRIBUTION,
    REFERENCE_WORKFLOW_KIND,
    build_llm_echo_summary_graph_definition,
    llm_echo_summary_workflow_contribution,
)


def test_llm_echo_summary_contribution_shape() -> None:
    contribution = llm_echo_summary_workflow_contribution()

    assert contribution.kind == REFERENCE_WORKFLOW_KIND
    assert contribution.definition.kind == REFERENCE_WORKFLOW_KIND
    assert contribution.definition.metadata.name == 'LLM Echo Summary'
    assert contribution.definition.metadata.tags == ('reference', 'diagnostic')
    assert contribution.definition.requirements.provider_profiles == ('default',)
    assert contribution.definition.requirements.tools == ('echo',)
    assert contribution.definition.requirements.artifact_store is False
    assert contribution.definition.requirements.checkpoint_store is False
    assert contribution.definition.requirements.event_sinks == ()
    assert contribution.definition.build is build_llm_echo_summary_graph_definition
    assert contribution.metadata['graph_kind'] == 'llm_echo_summary'
    assert callable(contribution.definition.build)


def test_llm_echo_summary_module_constant_matches_factory() -> None:
    assert LLM_ECHO_SUMMARY_WORKFLOW_CONTRIBUTION.kind == REFERENCE_WORKFLOW_KIND
    assert LLM_ECHO_SUMMARY_WORKFLOW_CONTRIBUTION.definition.kind == REFERENCE_WORKFLOW_KIND
