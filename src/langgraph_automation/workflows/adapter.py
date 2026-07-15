"""Internal adapter for turning workflow definitions into graph objects."""

from __future__ import annotations

from langgraph_automation.api.errors import RuntimeAssemblyError
from langgraph_automation.api.workflow import WorkflowDefinition

_WORKFLOW_ADAPTER_COMPONENT = "workflow_adapter"


def build_workflow_graph(definition: WorkflowDefinition) -> object:
    """Build the internal graph object for a workflow definition."""

    try:
        graph = definition.build()
    except RuntimeAssemblyError:
        raise
    except Exception as exc:
        raise RuntimeAssemblyError(
            f"Workflow build failed: workflow kind '{definition.kind}' could not be built.",
            code="WORKFLOW_BUILD_FAILED",
            component=_WORKFLOW_ADAPTER_COMPONENT,
            metadata={"workflow_kind": definition.kind},
        ) from exc

    if graph is None:
        raise RuntimeAssemblyError(
            f"Workflow build failed: workflow kind '{definition.kind}' returned no graph.",
            code="WORKFLOW_BUILD_INVALID_RESULT",
            component=_WORKFLOW_ADAPTER_COMPONENT,
            metadata={"workflow_kind": definition.kind},
        )

    return graph
