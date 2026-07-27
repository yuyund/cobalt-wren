"""Convenience entrypoint for the official LlamaIndex Workflows integration."""

from __future__ import annotations

from collections.abc import Mapping

from cobalt_wren.api.integrations import IntegrationContext
from cobalt_wren.integrations.workflows.llamaindex_provider import (
    LLAMAINDEX_WORKFLOWS_PROVIDER,
)


def integrate_llamaindex_workflow(
    target: object,
    *,
    workflow_kind: str,
    run_kwargs: Mapping[str, object] | None = None,
) -> object:
    """Wrap a LlamaIndex Workflow for foundation execution and projection."""

    return LLAMAINDEX_WORKFLOWS_PROVIDER.wrap(
        target,
        context=IntegrationContext(
            workflow_kind=workflow_kind,
            config={"run_kwargs": dict(run_kwargs or {})},
        ),
    )


__all__ = ["integrate_llamaindex_workflow"]
