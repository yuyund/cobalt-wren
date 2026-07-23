"""Tests for preparing the built-in reference workflow."""

from __future__ import annotations

from langgraph_automation.runtime.dependencies import RuntimeDependencies
from langgraph_automation.workflows.catalog import create_builtin_workflow_registry
from langgraph_automation.workflows.prepare import WorkflowPreparer


def test_reference_llm_echo_summary_prepares_through_builtin_registry() -> None:
    registry = create_builtin_workflow_registry()
    prepared = WorkflowPreparer(
        registry,
    ).prepare(
        workflow_kind='reference.llm_echo_summary',
        dependencies=RuntimeDependencies(
            providers={'default': object()},
            tools={'echo': object()},
            artifact_store=None,
            checkpoint_store=None,
            event_sinks={},
        ),
    )

    assert prepared.kind == 'reference.llm_echo_summary'
    assert prepared.definition.kind == 'reference.llm_echo_summary'
    assert prepared.executable is not None
