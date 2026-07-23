"""Tests for the internal workflow adapter boundary."""

from __future__ import annotations

import pytest

from langgraph_automation.api.errors import RuntimeAssemblyError
from langgraph_automation.api.workflow import (
    WorkflowBuildContext,
    WorkflowDefinition,
    WorkflowExecutionResult,
    WorkflowMetadata,
    WorkflowRequirements,
)
from langgraph_automation.workflows.adapter import build_workflow_graph, execute_workflow


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


def test_build_workflow_graph_passes_public_context() -> None:
    seen: list[WorkflowBuildContext] = []

    def build(context: WorkflowBuildContext) -> object:
        seen.append(context)
        return object()

    context = WorkflowBuildContext(
        workflow_kind="external.kind", config={"mode": "free"}, providers={"p": object()}
    )
    build_workflow_graph(_workflow_definition(build), context)

    assert seen == [context]
    assert context.config == {"mode": "free"}


def test_execute_workflow_supports_execute_invoke_and_callable() -> None:
    class ExecuteObject:
        def execute(self, payload):
            return WorkflowExecutionResult(output={"path": "execute", **payload})

    class InvokeObject:
        def invoke(self, payload):
            return {"path": "invoke", **payload}

    assert execute_workflow(ExecuteObject(), {"x": 1}).output["path"] == "execute"
    assert execute_workflow(InvokeObject(), {"x": 1}).output["path"] == "invoke"
    assert execute_workflow(lambda payload: {"path": "callable", **payload}, {"x": 1}).output["path"] == "callable"


def test_execute_workflow_rejects_unsupported_object_and_result() -> None:
    with pytest.raises(RuntimeAssemblyError) as excinfo:
        execute_workflow(object(), {})
    assert excinfo.value.code == "WORKFLOW_EXECUTION_FAILED"

    with pytest.raises(RuntimeAssemblyError) as excinfo:
        execute_workflow(lambda _: "invalid", {})
    assert excinfo.value.code == "WORKFLOW_EXECUTION_INVALID_RESULT"


def test_execute_workflow_defensively_copies_input_and_mapping_result() -> None:
    original = {"items": ["original"]}
    returned = {"status": "done"}

    def executable(payload):
        payload["added"] = True
        return returned

    result = execute_workflow(executable, original)
    returned["status"] = "mutated"

    assert original == {"items": ["original"]}
    assert result.output == {"status": "done"}


def test_execute_workflow_safe_wrap_does_not_expose_internal_exception() -> None:
    def executable(_payload):
        raise ValueError("private token abc123")

    with pytest.raises(RuntimeAssemblyError) as excinfo:
        execute_workflow(executable, {})

    assert excinfo.value.code == "WORKFLOW_EXECUTION_FAILED"
    assert "private token" not in str(excinfo.value)
    assert isinstance(excinfo.value.__cause__, ValueError)
