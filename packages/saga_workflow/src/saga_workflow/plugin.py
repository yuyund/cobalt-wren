from __future__ import annotations

from typing import cast

from cobalt_wren.api.plugins import Plugin, PluginContributions, PluginMetadata
from cobalt_wren.api.stores import ArtifactStore, CheckpointStore
from cobalt_wren.api.workflow import WorkflowBuildContext, WorkflowContribution, WorkflowDefinition, WorkflowMetadata, WorkflowRequirements

from .workflow import SagaExecutable

WORKFLOW_KIND = "saga.order_fulfillment"


def create_plugin() -> Plugin:
    def build(context: WorkflowBuildContext) -> SagaExecutable:
        return SagaExecutable(
            artifact_store=cast(ArtifactStore, context.require_artifact_store()),
            checkpoint_store=cast(CheckpointStore, context.require_checkpoint_store()),
        )

    contribution = WorkflowContribution(
        kind=WORKFLOW_KIND,
        definition=WorkflowDefinition(
            kind=WORKFLOW_KIND,
            metadata=WorkflowMetadata(
                name="Order Fulfillment Saga",
                description="Parallel partial-failure workflow with retry and compensation.",
                tags=("saga", "parallel", "partial-failure", "compensation"),
                metadata={"framework": "langgraph"},
            ),
            requirements=WorkflowRequirements(artifact_store=True, checkpoint_store=True),
            build=build,
            extra={
                "lifecycle_events_owner": "control_plane",
                "capabilities": ["parallel-branches", "partial-failure", "individual-retry", "compensation", "reconciliation"],
                "resume_actions": {
                    "retry_failed": {"title": "Retry failed branches", "payload": {"action": "retry_failed"}, "schema": {"type": "object", "properties": {}}},
                    "compensate": {"title": "Compensate successful branches", "danger": True, "payload": {"action": "compensate"}, "schema": {"type": "object", "properties": {}}},
                },
            },
        ),
    )
    return Plugin(
        metadata=PluginMetadata(
            name="saga-workflow",
            version="0.1.0",
            description="External Saga workflow distribution.",
            plugin_types=("workflow",),
            provides={"workflows": (WORKFLOW_KIND,)},
        ),
        contributions=PluginContributions(workflows=(contribution,)),
    )
