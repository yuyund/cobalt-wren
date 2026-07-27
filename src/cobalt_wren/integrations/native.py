"""Convenience entrypoint for the official Native Authoring integration."""

from __future__ import annotations

from cobalt_wren.api.integrations import IntegrationContext
from cobalt_wren.api.workflow import WorkflowBuildContext
from cobalt_wren.integrations.workflows.native_provider import NATIVE_PROVIDER


def integrate_native_workflow(
    target: object,
    *,
    workflow_kind: str,
    build_context: WorkflowBuildContext,
) -> object:
    """Wrap a Native authoring object for generic foundation execution."""

    return NATIVE_PROVIDER.wrap(
        target,
        context=IntegrationContext(
            workflow_kind=workflow_kind,
            config={"build_context": build_context},
        ),
    )


__all__ = ["integrate_native_workflow"]
