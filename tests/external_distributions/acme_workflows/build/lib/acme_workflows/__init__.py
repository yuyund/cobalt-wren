"""Separately installed ACME workflow plugin."""
from __future__ import annotations
from collections.abc import Mapping
from dataclasses import dataclass
from langgraph_automation.api.plugins import Plugin, PluginContributions, PluginMetadata
from langgraph_automation.api.workflow import WorkflowBuildContext, WorkflowContribution, WorkflowDefinition, WorkflowMetadata, WorkflowRequirements

WORKFLOW_KIND = "acme.installed_review"

@dataclass(frozen=True, slots=True)
class InstalledWorkflow:
    prefix: str
    def execute(self, input_payload: Mapping[str, object]) -> Mapping[str, object]:
        return {"message": f"{self.prefix}:{input_payload['request_id']}"}

def create_plugin() -> Plugin:
    def build(context: WorkflowBuildContext) -> InstalledWorkflow:
        return InstalledWorkflow(prefix=str(context.config.get("prefix", "installed")))
    workflow = WorkflowContribution(
        kind=WORKFLOW_KIND,
        definition=WorkflowDefinition(
            kind=WORKFLOW_KIND,
            metadata=WorkflowMetadata(name="Installed ACME Review", version="1.0.0"),
            requirements=WorkflowRequirements(),
            build=build,
        ),
    )
    return Plugin(
        metadata=PluginMetadata(name="acme.installed_workflows", version="1.0.0", plugin_types=("workflow",)),
        contributions=PluginContributions(workflows=(workflow,)),
    )

__all__ = ["WORKFLOW_KIND", "create_plugin"]
