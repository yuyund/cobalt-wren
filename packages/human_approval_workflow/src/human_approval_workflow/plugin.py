"""Plugin registration for the human approval workflow."""
from __future__ import annotations

from typing import cast

from langgraph_automation.api.plugins import Plugin, PluginContributions, PluginMetadata
from langgraph_automation.api.stores import ArtifactStore, CheckpointStore
from langgraph_automation.api.workflow import (
    WorkflowBuildContext,
    WorkflowContribution,
    WorkflowDefinition,
    WorkflowMetadata,
    WorkflowRequirements,
)

from .workflow import HumanApprovalExecutable

WORKFLOW_KIND = "human.approval"


def create_plugin() -> Plugin:
    def build(context: WorkflowBuildContext) -> HumanApprovalExecutable:
        return HumanApprovalExecutable(
            artifact_store=cast(ArtifactStore, context.require_artifact_store()),
            checkpoint_store=cast(CheckpointStore, context.require_checkpoint_store()),
        )

    contribution = WorkflowContribution(
        kind=WORKFLOW_KIND,
        definition=WorkflowDefinition(
            kind=WORKFLOW_KIND,
            metadata=WorkflowMetadata(
                name="Human Approval",
                description="Pauses for approve, reject, or revise input and resumes durably.",
                version="0.1.0",
                tags=("human-in-the-loop", "pause", "resume", "approval"),
                metadata={"framework": "langgraph"},
            ),
            requirements=WorkflowRequirements(artifact_store=True, checkpoint_store=True),
            build=build,
            input_schema={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "proposal": {"type": "string"},
                },
                "required": ["title", "proposal"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "decision": {"enum": ["approved", "rejected"]},
                    "artifact_key": {"type": "string"},
                },
            },
            extra={
                "lifecycle_events_owner": "control_plane",
                "capabilities": ["pause", "resume", "human-input", "revision-loop"],
                "resume_actions": {
                    "approve": {
                        "title": "Approve",
                        "payload": {"decision": "approve"},
                        "schema": {"type": "object", "properties": {"note": {"type": "string", "title": "Reviewer note"}}},
                    },
                    "reject": {
                        "title": "Reject",
                        "danger": True,
                        "payload": {"decision": "reject"},
                        "schema": {"type": "object", "properties": {"note": {"type": "string", "title": "Reason"}}},
                    },
                    "revise": {
                        "title": "Request revision",
                        "payload": {"decision": "revise"},
                        "schema": {
                            "type": "object",
                            "properties": {
                                "proposal": {"type": "string", "title": "Revised proposal", "format": "textarea"},
                                "note": {"type": "string", "title": "Reviewer note"},
                            },
                            "required": ["proposal"],
                        },
                    },
                },
            },
        ),
    )
    return Plugin(
        metadata=PluginMetadata(
            name="human-approval-workflow",
            version="0.1.0",
            description="External LangGraph human approval workflow.",
            plugin_types=("workflow",),
            provides={"workflows": (WORKFLOW_KIND,)},
        ),
        contributions=PluginContributions(workflows=(contribution,)),
    )
