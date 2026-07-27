"""Convenience entrypoint for the official LangGraph integration."""

from __future__ import annotations

from collections.abc import Mapping

from cobalt_wren.api.integrations import IntegrationContext
from cobalt_wren.integrations.workflows.langgraph_provider import (
    LANGGRAPH_PROVIDER,
)


def integrate_langgraph(
    target: object,
    *,
    workflow_kind: str,
    output_key: str | None = None,
    invoke_config: Mapping[str, object] | None = None,
) -> object:
    """Wrap a compiled LangGraph object for foundation execution and projection."""

    config: dict[str, object] = {"invoke_config": dict(invoke_config or {})}
    if output_key is not None:
        config["output_key"] = output_key
    return LANGGRAPH_PROVIDER.wrap(
        target,
        context=IntegrationContext(workflow_kind=workflow_kind, config=config),
    )


__all__ = ["integrate_langgraph"]
