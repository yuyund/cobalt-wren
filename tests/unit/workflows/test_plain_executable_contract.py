"""Lowest-level plain Python executable compatibility contract."""

from __future__ import annotations

from collections.abc import Mapping

from cobalt_wren.api.workflow import (
    WorkflowBuildContext,
    WorkflowDefinition,
    WorkflowExecutionContext,
    WorkflowExecutionResult,
    WorkflowMetadata,
    WorkflowRequirements,
)
from cobalt_wren.workflows.adapter import build_workflow_graph


class PlainExecutable:
    def execute(
        self,
        input_payload: Mapping[str, object],
        *,
        context: WorkflowExecutionContext,
    ) -> WorkflowExecutionResult:
        return WorkflowExecutionResult(
            output={"value": input_payload.get("value")},
            metadata={"thread_id": context.thread_id, "framework": "none"},
        )


def test_generic_adapter_accepts_plain_python_executable_without_provider() -> None:
    executable = PlainExecutable()
    definition = WorkflowDefinition(
        kind="test.plain-executable",
        metadata=WorkflowMetadata(
            name="Plain executable",
            metadata={"framework": "none"},
        ),
        requirements=WorkflowRequirements(),
        build=lambda context: executable,
    )

    built = build_workflow_graph(
        definition,
        WorkflowBuildContext(workflow_kind=definition.kind),
    )
    result = built.execute(
        {"value": "ok"},
        context=WorkflowExecutionContext(thread_id="plain-thread"),
    )

    assert built is executable
    assert result.output == {"value": "ok"}
    assert result.metadata == {
        "thread_id": "plain-thread",
        "framework": "none",
    }
