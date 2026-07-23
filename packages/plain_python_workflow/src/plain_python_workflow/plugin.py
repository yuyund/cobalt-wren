from __future__ import annotations

from typing import cast

from langgraph_automation.api.plugins import Plugin, PluginContributions, PluginMetadata
from langgraph_automation.api.stores import ArtifactStore, CheckpointStore
from langgraph_automation.api.workflow import WorkflowBuildContext, WorkflowContribution, WorkflowDefinition, WorkflowMetadata, WorkflowRequirements

from .workflow import PlainPythonExecutable

WORKFLOW_KIND = "plain.confirmation"


def create_plugin() -> Plugin:
    def build(context: WorkflowBuildContext) -> PlainPythonExecutable:
        return PlainPythonExecutable(
            artifact_store=cast(ArtifactStore, context.require_artifact_store()),
            checkpoint_store=cast(CheckpointStore, context.require_checkpoint_store()),
        )

    contribution = WorkflowContribution(
        kind=WORKFLOW_KIND,
        definition=WorkflowDefinition(
            kind=WORKFLOW_KIND,
            metadata=WorkflowMetadata(
                name="Plain Python Confirmation",
                description="Framework-free JSON state machine with durable resume.",
                version="0.1.0",
                tags=("plain-python", "pause", "resume"),
                metadata={"framework": "none", "state_schema_version": 1},
            ),
            requirements=WorkflowRequirements(artifact_store=True, checkpoint_store=True),
            build=build,
            input_schema={
                "type": "object",
                "properties": {
                    "subject": {"type": "string", "title": "Subject"},
                    "message": {"type": "string", "title": "Message"},
                },
                "required": ["subject", "message"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "decision": {"enum": ["confirmed", "cancelled"]},
                    "artifact_key": {"type": "string"},
                },
            },
            extra={
                "lifecycle_events_owner": "control_plane",
                "capabilities": ["pause", "resume", "framework-free", "versioned-state"],
                "resume_actions": {
                    "confirm": {
                        "title": "Confirm",
                        "schema": {
                            "type": "object",
                            "properties": {"note": {"type": "string", "title": "Note"}},
                        },
                    },
                    "cancel": {
                        "title": "Cancel",
                        "schema": {
                            "type": "object",
                            "properties": {"reason": {"type": "string", "title": "Reason"}},
                        },
                    },
                },
            },
        ),
    )
    return Plugin(
        metadata=PluginMetadata(
            name="plain-python-workflow",
            version="0.1.0",
            description="Framework-free external workflow distribution.",
            plugin_types=("workflow",),
            provides={"workflows": (WORKFLOW_KIND,)},
        ),
        contributions=PluginContributions(workflows=(contribution,)),
    )
