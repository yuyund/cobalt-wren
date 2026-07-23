"""Public workflow facade import coverage."""

from __future__ import annotations


def test_public_workflow_api_exports() -> None:
    from langgraph_automation.api.workflow import (
        WorkflowContribution,
        WorkflowDefinition,
        WorkflowMetadata,
        WorkflowRequirements,
        WorkflowResumeRequest,
        WorkflowResumable,
    )

    assert WorkflowContribution is not None
    assert WorkflowDefinition is not None
    assert WorkflowMetadata is not None
    assert WorkflowRequirements is not None
    assert WorkflowResumeRequest is not None
    assert WorkflowResumable is not None


def test_public_workflow_api_all() -> None:
    import langgraph_automation.api.workflow as workflow_api

    assert set(workflow_api.__all__) == {
        "WorkflowBuildContext",
        "WorkflowExecutionContext",
        "WorkflowExecutionControl",
        "WorkflowResumeRequest",
        "WorkflowExecutionResult",
        "WorkflowExecutable",
        "WorkflowResumable",
        "WorkflowMetadata",
        "WorkflowRequirements",
        "WorkflowDefinition",
        "WorkflowContribution",
    }


def test_public_workflow_api_does_not_export_graph_runtime_names() -> None:
    import langgraph_automation.api.workflow as workflow_api

    assert not hasattr(workflow_api, "GraphDefinition")
    assert not hasattr(workflow_api, "GraphRuntime")
    assert not hasattr(workflow_api, "GraphRuntimeConfig")
