"""Explicit workflow preparation helper for service-level tooling."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from langgraph_automation.api.engine import EnginePreparedWorkflow, create_engine
from langgraph_automation.api.plugins import Plugin


def prepare_run_workflow(
    *,
    workflow_kind: str,
    config: Mapping[str, object],
    plugins: Sequence[Plugin] = (),
) -> EnginePreparedWorkflow:
    engine = create_engine(config, plugins=plugins)
    return engine.prepare_workflow(workflow_kind)
