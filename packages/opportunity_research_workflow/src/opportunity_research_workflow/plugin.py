"""Plugin registration for the opportunity research workflow."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import cast

from langgraph_automation.api.plugins import (
    Plugin,
    PluginContributions,
    PluginMetadata,
    ToolContribution,
)
from langgraph_automation.api.stores import ArtifactStore, CheckpointStore
from langgraph_automation.api.workflow import (
    WorkflowBuildContext,
    WorkflowContribution,
    WorkflowDefinition,
    WorkflowMetadata,
    WorkflowRequirements,
)
from langgraph_automation.integrations.llm.base import LLMClient
from langgraph_automation.integrations.tools.base import ToolCallable

from .search import SearXNGSearchTool
from .workflow import OpportunityResearchExecutable

PLUGIN_NAME = "opportunity-research-workflow"
WORKFLOW_KIND = "opportunity.research"
SEARCH_TOOL_NAME = "searxng.search"
SearchFactory = Callable[[Mapping[str, object]], ToolCallable]


def _default_search_factory(config: Mapping[str, object]) -> ToolCallable:
    return SearXNGSearchTool(
        base_url=str(config.get("base_url", "http://localhost:8080")).strip(),
        timeout_seconds=_as_float(config.get("timeout_seconds"), 10.0),
        max_results=_as_int(config.get("max_results"), 8),
    )


def create_plugin(*, search_factory: SearchFactory | None = None) -> Plugin:
    effective_search_factory = search_factory or _default_search_factory

    def create_search_tool(*, config: object, context: object) -> object:
        del context
        mapping = config if isinstance(config, Mapping) else {}
        return effective_search_factory(mapping)

    def build(context: WorkflowBuildContext) -> OpportunityResearchExecutable:
        return OpportunityResearchExecutable(
            llm=cast(LLMClient, context.require_provider("research")),
            search=cast(ToolCallable, context.require_tool(SEARCH_TOOL_NAME)),
            artifact_store=cast(ArtifactStore, context.require_artifact_store()),
            checkpoint_store=cast(CheckpointStore, context.require_checkpoint_store()),
            default_max_retries=_as_int(context.config.get("max_retries"), 1),
            default_wait_seconds=_as_float(context.config.get("wait_seconds"), 0.0),
            minimum_sources=_as_int(context.config.get("minimum_sources"), 4),
        )

    workflow = WorkflowContribution(
        kind=WORKFLOW_KIND,
        definition=WorkflowDefinition(
            kind=WORKFLOW_KIND,
            metadata=WorkflowMetadata(
                name="Opportunity Research",
                description=(
                    "Researches evidence-backed revenue opportunity hypotheses "
                    "without executing them."
                ),
                version="0.1.0",
                tags=(
                    "research",
                    "searxng",
                    "llm",
                    "report",
                    "revenue-opportunity",
                ),
                metadata={"research_only": True, "execution_actions": False},
            ),
            requirements=WorkflowRequirements(
                provider_profiles=("research",),
                tools=(SEARCH_TOOL_NAME,),
                artifact_store=True,
                checkpoint_store=True,
            ),
            build=build,
            input_schema={
                "type": "object",
                "properties": {
                    "theme": {"type": "string", "minLength": 1},
                    "constraints": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "max_opportunities": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 10,
                    },
                },
                "required": ["theme"],
                "additionalProperties": True,
            },
            output_schema={
                "type": "object",
                "properties": {
                    "status": {"enum": ["completed", "needs_review"]},
                    "opportunities": {"type": "array"},
                    "artifact_keys": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "research_only": {"const": True},
                },
                "required": [
                    "status",
                    "opportunities",
                    "artifact_keys",
                    "research_only",
                ],
            },
            extra={
                "lifecycle_events_owner": "control_plane",
                "capabilities": [
                    "parallel-search",
                    "bounded-retry",
                    "conditional-routing",
                    "parallel-verification",
                    "artifact-report",
                    "checkpoint",
                ],
                "safety": {
                    "research_only": True,
                    "prohibited_actions": [
                        "purchase",
                        "payment",
                        "outreach",
                        "posting",
                        "account_creation",
                    ],
                },
            },
        ),
        validate_config=_validate_workflow_config,
        metadata={"distribution": "opportunity-research-workflow"},
    )
    return Plugin(
        metadata=PluginMetadata(
            name=PLUGIN_NAME,
            version="0.1.0",
            description="External opportunity research workflow and SearXNG tool.",
            plugin_types=("workflow", "tool"),
            provides={
                "workflows": (WORKFLOW_KIND,),
                "tools": (SEARCH_TOOL_NAME,),
            },
            metadata={
                "distribution": "opportunity-research-workflow",
                "research_only": True,
            },
        ),
        contributions=PluginContributions(
            workflows=(workflow,),
            tools=(
                ToolContribution(
                    name=SEARCH_TOOL_NAME,
                    description="SearXNG-compatible JSON search tool.",
                    capabilities=("web-search", "research"),
                    input_schema={
                        "type": "object",
                        "properties": {"query": {"type": "string"}},
                        "required": ["query"],
                    },
                    output_schema={
                        "type": "array",
                        "items": {"type": "object"},
                    },
                    safety_metadata={"network_access": True, "read_only": True},
                    validate_config=_validate_search_config,
                    create_tool=create_search_tool,
                ),
            ),
        ),
    )


def _validate_search_config(*, config: object, context: object) -> None:
    del context
    if not isinstance(config, Mapping):
        raise ValueError("SearXNG tool config must be a mapping")
    base_url = str(config.get("base_url", "http://localhost:8080"))
    if not base_url.startswith(("http://", "https://")):
        raise ValueError("SearXNG base_url must use http or https")


def _validate_workflow_config(*, config: Mapping[str, object]) -> None:
    if _as_int(config.get("max_retries"), 1) not in range(0, 4):
        raise ValueError("max_retries must be between 0 and 3")
    if _as_float(config.get("wait_seconds"), 0.0) < 0:
        raise ValueError("wait_seconds must be non-negative")


def _as_int(value: object, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, (float, str)):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default
    return default


def _as_float(value: object, default: float) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    return default
