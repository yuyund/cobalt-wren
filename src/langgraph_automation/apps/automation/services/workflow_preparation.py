"""Workflow preparation bridge for the control-plane service layer."""

from __future__ import annotations

from langgraph_automation.plugins.registry import PluginRegistry
from langgraph_automation.runtime.dependencies import RuntimeDependencies
from langgraph_automation.workflows.catalog import create_builtin_workflow_registry
from langgraph_automation.workflows.prepare import PreparedWorkflow, prepare_workflow

CANONICAL_REFERENCE_WORKFLOW_KIND = 'reference.llm_echo_summary'
WORKFLOW_KIND_ALIASES = {
    'llm_echo_summary': CANONICAL_REFERENCE_WORKFLOW_KIND,
}


def canonicalize_workflow_kind(workflow_kind: str) -> str:
    return WORKFLOW_KIND_ALIASES.get(workflow_kind, workflow_kind)


def prepare_run_workflow(
    *,
    workflow_kind: str,
    dependencies: RuntimeDependencies,
    registry: PluginRegistry | None = None,
) -> PreparedWorkflow:
    effective_registry = registry if registry is not None else create_builtin_workflow_registry()
    canonical_kind = canonicalize_workflow_kind(workflow_kind)
    return prepare_workflow(workflow_kind=canonical_kind, registry=effective_registry, dependencies=dependencies)


def resolve_graph_for_run(
    *,
    workflow_kind: str,
    dependencies: RuntimeDependencies,
    registry: PluginRegistry | None = None,
) -> object:
    prepared = prepare_run_workflow(workflow_kind=workflow_kind, dependencies=dependencies, registry=registry)
    return prepared.graph
