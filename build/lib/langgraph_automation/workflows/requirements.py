"""Internal workflow requirement checks."""

from __future__ import annotations

from langgraph_automation.api.errors import RuntimeAssemblyError
from langgraph_automation.api.workflow import WorkflowRequirements
from langgraph_automation.runtime.dependencies import RuntimeDependencies

_WORKFLOW_REQUIREMENTS_COMPONENT = "workflow_requirements"


def check_workflow_requirements(requirements: WorkflowRequirements, dependencies: RuntimeDependencies) -> None:
    """Ensure a runtime dependency bundle satisfies workflow requirements."""

    for provider_profile in requirements.provider_profiles:
        if provider_profile not in dependencies.providers:
            raise _missing_requirement_error("provider_profile", provider_profile)

    for tool_name in requirements.tools:
        if tool_name not in dependencies.tools:
            raise _missing_requirement_error("tool", tool_name)

    if requirements.artifact_store and dependencies.artifact_store is None:
        raise _missing_requirement_error("artifact_store", "artifact")

    if requirements.checkpoint_store and dependencies.checkpoint_store is None:
        raise _missing_requirement_error("checkpoint_store", "checkpoint")

    for sink_name in requirements.event_sinks:
        if sink_name not in dependencies.event_sinks:
            raise _missing_requirement_error("event_sink", sink_name)


def _missing_requirement_error(requirement_type: str, requirement_name: str) -> RuntimeAssemblyError:
    return RuntimeAssemblyError(
        f"Workflow requirement failed: missing {requirement_type} '{requirement_name}'.",
        code="WORKFLOW_REQUIREMENT_MISSING",
        component=_WORKFLOW_REQUIREMENTS_COMPONENT,
        metadata={
            "requirement_type": requirement_type,
            "requirement_name": requirement_name,
            "workflow_stage": "requirements",
        },
    )
