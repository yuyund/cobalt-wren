"""Internal adapters for public workflow build and execution contracts."""

from __future__ import annotations

from collections.abc import Mapping
import inspect
from typing import Any, Protocol, cast

from langgraph_automation.api.errors import RuntimeAssemblyError
from langgraph_automation.api.workflow import (
    WorkflowBuildContext,
    WorkflowDefinition,
    WorkflowExecutionContext,
    WorkflowExecutionResult,
)

_WORKFLOW_ADAPTER_COMPONENT = "workflow_adapter"


class _ExecuteCapable(Protocol):
    def execute(self, input_payload: Mapping[str, object], **kwargs: object) -> object: ...


class _InvokeCapable(Protocol):
    def invoke(self, input_payload: Mapping[str, object]) -> object: ...


def build_workflow_graph(definition: WorkflowDefinition, context: WorkflowBuildContext | None = None) -> object:
    """Build an opaque workflow object without imposing a graph framework."""

    context = context or WorkflowBuildContext(workflow_kind=definition.kind)
    try:
        parameters = inspect.signature(definition.build).parameters
        graph = definition.build() if len(parameters) == 0 else definition.build(context)
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


def execute_workflow(
    executable: object,
    input_payload: Mapping[str, object] | None = None,
    *,
    context: WorkflowExecutionContext | None = None,
) -> WorkflowExecutionResult:
    """Execute an opaque workflow through a small capability-based adapter."""

    payload = dict(input_payload or {})
    try:
        if callable(getattr(executable, "execute", None)):
            method = cast(_ExecuteCapable, executable).execute
            parameters = inspect.signature(method).parameters
            result = method(payload, context=context or WorkflowExecutionContext()) if "context" in parameters else method(payload)
        elif callable(getattr(executable, "invoke", None)):
            result = cast(_InvokeCapable, executable).invoke(payload)
        elif callable(executable):
            result = cast(Any, executable)(payload)
        else:
            raise TypeError("workflow object exposes no execute, invoke, or callable capability")
    except RuntimeAssemblyError:
        raise
    except Exception as exc:
        raise RuntimeAssemblyError(
            "Workflow execution failed.",
            code="WORKFLOW_EXECUTION_FAILED",
            component=_WORKFLOW_ADAPTER_COMPONENT,
        ) from exc

    if isinstance(result, WorkflowExecutionResult):
        return result
    if isinstance(result, Mapping):
        return WorkflowExecutionResult(output=result)
    raise RuntimeAssemblyError(
        "Workflow execution failed: workflow returned an unsupported result.",
        code="WORKFLOW_EXECUTION_INVALID_RESULT",
        component=_WORKFLOW_ADAPTER_COMPONENT,
    )
