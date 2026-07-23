from __future__ import annotations

from langgraph_automation.api.errors import ExecutionError, WorkflowPreparationError


def test_workflow_preparation_error_has_stable_safe_shape() -> None:
    error = WorkflowPreparationError(
        "Workflow preparation failed.", code="WORKFLOW_PREPARATION_FAILED", component="workflow"
    )
    assert error.to_safe_dict() == {
        "category": "workflow_preparation",
        "code": "WORKFLOW_PREPARATION_FAILED",
        "safe_message": "Workflow preparation failed.",
        "component": "workflow",
    }


def test_execution_error_has_stable_safe_shape() -> None:
    error = ExecutionError(
        "Workflow execution failed.",
        code="WORKFLOW_EXECUTION_FAILED",
        component="execution",
        retryable=False,
    )
    assert error.to_safe_dict()["category"] == "execution"
    assert error.to_safe_dict()["retryable"] is False
