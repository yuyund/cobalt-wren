"""Separately distributed workflow contribution used for extension testing."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from cobalt_wren.api.plugins import Plugin, PluginContributions, PluginMetadata
from cobalt_wren.api.stores import ArtifactWriteRequest, CheckpointWriteRequest
from cobalt_wren.api.workflow import (
    WorkflowBuildContext,
    WorkflowContribution,
    WorkflowDefinition,
    WorkflowMetadata,
    WorkflowRequirements,
)

EXTERNAL_PLUGIN_NAME = "acme.workflows"
EXTERNAL_WORKFLOW_KIND = "acme.review_request"


@dataclass(frozen=True, slots=True)
class ExternalGraph:
    """Opaque executable owned entirely by the external package."""

    workflow_kind: str
    prefix: str = "review"
    provider: object | None = None
    tool: object | None = None
    artifact_store: object | None = None
    checkpoint_store: object | None = None
    event_sink: object | None = None
    contract_version: int = 1

    def execute(self, input_payload: Mapping[str, object]) -> Mapping[str, object]:
        request_id = str(input_payload.get("request_id", ""))
        output: dict[str, object] = {
            "status": "accepted",
            "message": f"{self.prefix}:{request_id}",
        }
        if self.provider is not None:
            output["provider"] = self.provider.complete(request_id)
        if self.tool is not None:
            output["tool"] = self.tool(request_id)
        if self.artifact_store is not None:
            stored = self.artifact_store.put(ArtifactWriteRequest(
                run_id=request_id, storage_key=f"reviews/{request_id}.txt",
                body=request_id.encode(), name="review", kind="text",
            ))
            output["artifact_key"] = stored.storage_key
        if self.checkpoint_store is not None:
            checkpoint = self.checkpoint_store.save(CheckpointWriteRequest(
                run_id=request_id, checkpoint_id="reviewed", body=request_id.encode(),
                serializer_name="raw", serializer_version=1, content_type="application/octet-stream",
            ))
            output["checkpoint_id"] = checkpoint.checkpoint_id
        if self.event_sink is not None:
            self.event_sink.semantic_event(1, "acme.reviewed", payload={"request_id": request_id})
            output["event_emitted"] = True
        return output


def create_plugin(
    *,
    on_build: Callable[[], None] | None = None,
    requirements: WorkflowRequirements | None = None,
) -> Plugin:
    """Return the package's public plugin contribution."""

    def build(context: WorkflowBuildContext) -> ExternalGraph:
        if on_build is not None:
            on_build()
        provider = context.providers.get("external-profile")
        tool = context.tools.get("external.tool")
        return ExternalGraph(
            workflow_kind=EXTERNAL_WORKFLOW_KIND,
            prefix=str(context.config.get("prefix", "review")),
            provider=provider,
            tool=tool,
            artifact_store=context.artifact_store if effective_requirements.artifact_store else None,
            checkpoint_store=context.checkpoint_store if effective_requirements.checkpoint_store else None,
            event_sink=(
                context.event_sinks.get("external-events")
                if "external-events" in effective_requirements.event_sinks
                else None
            ),
        )

    effective_requirements = requirements or WorkflowRequirements()
    workflow = WorkflowContribution(
        kind=EXTERNAL_WORKFLOW_KIND,
        definition=WorkflowDefinition(
            kind=EXTERNAL_WORKFLOW_KIND,
            metadata=WorkflowMetadata(
                name="ACME Review Request",
                description="External package workflow used to prove package separation.",
                version="1.0.0",
                tags=("external", "review"),
                metadata={"owner": "acme", "ui_summary": "Review a bounded request."},
            ),
            requirements=effective_requirements,
            build=build,
            input_schema={
                "type": "object",
                "properties": {"request_id": {"type": "string"}},
                "required": ["request_id"],
                "additionalProperties": False,
            },
            output_schema={
                "type": "object",
                "properties": {"status": {"type": "string"}},
                "required": ["status"],
                "additionalProperties": False,
            },
            extra={"ui": {"summary_field": "status"}},
        ),
        metadata={"distribution": "acme-workflows"},
    )
    return Plugin(
        metadata=PluginMetadata(
            name=EXTERNAL_PLUGIN_NAME,
            version="1.0.0",
            description="External workflow-only plugin.",
            plugin_types=("workflow",),
            provides={"workflows": (EXTERNAL_WORKFLOW_KIND,)},
            metadata={"distribution": "acme-workflows"},
        ),
        contributions=PluginContributions(workflows=(workflow,)),
    )
