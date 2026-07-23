"""Workflow preparation path for execution readiness.

This module resolves workflow contributions, checks runtime requirements, and
builds the internal graph object without executing the workflow.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from langgraph_automation.api.errors import PluginResolutionError
from langgraph_automation.api.workflow import WorkflowBuildContext, WorkflowContribution, WorkflowDefinition
from langgraph_automation.plugins.registry import PluginRegistry
from langgraph_automation.runtime.dependencies import RuntimeDependencies
from langgraph_automation.workflows.adapter import build_workflow_graph
from langgraph_automation.workflows.requirements import check_workflow_requirements

_WORKFLOW_PREPARER_COMPONENT = "workflow_preparer"


@dataclass(frozen=True, slots=True)
class PreparedWorkflow:
    kind: str
    contribution: WorkflowContribution
    definition: WorkflowDefinition
    executable: object


class WorkflowPreparer:
    def __init__(self, registry: PluginRegistry) -> None:
        self._registry = registry

    def prepare(
        self,
        *,
        workflow_kind: str,
        dependencies: RuntimeDependencies,
        config: Mapping[str, object] | None = None,
    ) -> PreparedWorkflow:
        try:
            contribution = self._registry.get_workflow(workflow_kind)
        except PluginResolutionError as exc:
            raise PluginResolutionError(
                "Workflow preparation failed because the workflow kind is not registered.",
                code="WORKFLOW_PREPARATION_WORKFLOW_NOT_FOUND",
                component=_WORKFLOW_PREPARER_COMPONENT,
                metadata={"workflow_kind": workflow_kind},
            ) from exc

        definition = contribution.definition
        workflow_config = dict(config or {})
        _validate_workflow_config(contribution, workflow_config)
        check_workflow_requirements(definition.requirements, dependencies)
        context = WorkflowBuildContext(
            workflow_kind=workflow_kind,
            config=workflow_config,
            providers=dependencies.providers,
            tools=dependencies.tools,
            artifact_store=dependencies.artifact_store,
            checkpoint_store=dependencies.checkpoint_store,
            event_sinks=dependencies.event_sinks,
        )
        executable = build_workflow_graph(definition, context)
        return PreparedWorkflow(
            kind=contribution.kind,
            contribution=contribution,
            definition=definition,
            executable=executable,
        )


def prepare_workflow(
    *,
    workflow_kind: str,
    registry: PluginRegistry,
    dependencies: RuntimeDependencies,
    config: Mapping[str, object] | None = None,
) -> PreparedWorkflow:
    return WorkflowPreparer(registry).prepare(
        workflow_kind=workflow_kind, dependencies=dependencies, config=config
    )


def _validate_workflow_config(
    contribution: WorkflowContribution, config: Mapping[str, object]
) -> None:
    hook = contribution.validate_config
    if hook is None:
        return
    from langgraph_automation.api.errors import RuntimeAssemblyError

    try:
        hook(config=dict(config))
    except RuntimeAssemblyError:
        raise
    except Exception as exc:
        raise RuntimeAssemblyError(
            "Workflow configuration validation failed.",
            code="WORKFLOW_CONFIG_INVALID",
            component=_WORKFLOW_PREPARER_COMPONENT,
            metadata={"workflow_kind": contribution.kind, "workflow_stage": "config_validation"},
        ) from exc
