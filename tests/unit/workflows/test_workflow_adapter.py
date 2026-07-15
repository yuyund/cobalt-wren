"""Tests for the internal workflow adapter boundary."""

from __future__ import annotations

import pytest

from langgraph_automation.api.errors import RuntimeAssemblyError
from langgraph_automation.api.workflow import WorkflowDefinition, WorkflowMetadata, WorkflowRequirements
from langgraph_automation.workflows.adapter import build_workflow_graph


def _workflow_definition(build_callable):
    return WorkflowDefinition(
        kind='reference.llm_echo_summary',
        metadata=WorkflowMetadata(name='LLM Echo Summary'),
        requirements=WorkflowRequirements(),
        build=build_callable,
    )


def test_build_workflow_graph_returns_build_result() -> None:
    sentinel = object()
    calls: list[str] = []

    def build() -> object:
        calls.append('called')
        return sentinel

    result = build_workflow_graph(_workflow_definition(build))

    assert result is sentinel
    assert calls == ['called']


def test_build_workflow_graph_rejects_none_result() -> None:
    def build() -> object | None:
        return None

    with pytest.raises(RuntimeAssemblyError) as excinfo:
        build_workflow_graph(_workflow_definition(build))

    assert excinfo.value.code == 'WORKFLOW_BUILD_INVALID_RESULT'
    assert excinfo.value.component == 'workflow_adapter'


def test_build_workflow_graph_wraps_arbitrary_exception() -> None:
    def build() -> object:
        raise ValueError('boom')

    with pytest.raises(RuntimeAssemblyError) as excinfo:
        build_workflow_graph(_workflow_definition(build))

    assert excinfo.value.code == 'WORKFLOW_BUILD_FAILED'
    assert 'boom' not in str(excinfo.value)


def test_build_workflow_graph_preserves_runtime_assembly_error() -> None:
    original = RuntimeAssemblyError(
        'Workflow build failed: already wrapped.',
        code='WORKFLOW_BUILD_FAILED',
        component='workflow_adapter',
    )

    def build() -> object:
        raise original

    with pytest.raises(RuntimeAssemblyError) as excinfo:
        build_workflow_graph(_workflow_definition(build))

    assert excinfo.value is original
