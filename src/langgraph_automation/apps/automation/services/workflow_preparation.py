"""Workflow preparation bridge for the control-plane service layer."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from langgraph_automation.api.engine import EnginePreparedWorkflow, create_engine
from langgraph_automation.api.plugins import Plugin

CANONICAL_REFERENCE_WORKFLOW_KIND = 'reference.llm_echo_summary'
WORKFLOW_KIND_ALIASES = {
    'llm_echo_summary': CANONICAL_REFERENCE_WORKFLOW_KIND,
}


def canonicalize_workflow_kind(workflow_kind: str) -> str:
    return WORKFLOW_KIND_ALIASES.get(workflow_kind, workflow_kind)


def prepare_run_workflow(
    *,
    workflow_kind: str,
    config: Mapping[str, object],
    plugins: Sequence[Plugin] = (),
) -> EnginePreparedWorkflow:
    canonical_kind = canonicalize_workflow_kind(workflow_kind)
    engine = create_engine(config, plugins=plugins)
    return engine.prepare_workflow(canonical_kind)


def resolve_graph_for_run(
    *,
    workflow_kind: str,
    config: Mapping[str, object],
    plugins: Sequence[Plugin] = (),
) -> object:
    prepared = prepare_run_workflow(workflow_kind=workflow_kind, config=config, plugins=plugins)
    return prepared.graph
