"""Workflow definition behavior tests."""

from __future__ import annotations

from cobalt_wren.api.workflow import (
    WorkflowContribution,
    WorkflowDefinition,
    WorkflowMetadata,
    WorkflowRequirements,
)


def test_workflow_metadata_retains_and_copies_fields() -> None:
    metadata = {"team": "platform"}
    tags = ["reference", "summary"]

    workflow_metadata = WorkflowMetadata(
        name="company_agent",
        description="Company workflow",
        version="0.2.0",
        tags=tags,
        metadata=metadata,
    )

    assert workflow_metadata.name == "company_agent"
    assert workflow_metadata.description == "Company workflow"
    assert workflow_metadata.version == "0.2.0"
    assert workflow_metadata.tags == ("reference", "summary")
    assert workflow_metadata.metadata == metadata
    assert workflow_metadata.metadata is not metadata


def test_workflow_requirements_defaults_and_normalization() -> None:
    requirements = WorkflowRequirements(provider_profiles=["default"], tools=["github.search_issues"], artifact_store=True, checkpoint_store=False, event_sinks=["stdout"])

    assert requirements.provider_profiles == ("default",)
    assert requirements.tools == ("github.search_issues",)
    assert requirements.artifact_store is True
    assert requirements.checkpoint_store is False
    assert requirements.event_sinks == ("stdout",)

    defaults = WorkflowRequirements()
    assert defaults.provider_profiles == ()
    assert defaults.tools == ()
    assert defaults.artifact_store is False
    assert defaults.checkpoint_store is False
    assert defaults.event_sinks == ()


def test_workflow_definition_retains_callable_and_copies_mappings() -> None:
    build_calls: list[str] = []
    input_schema = {"type": "object"}
    output_schema = {"type": "object"}
    extra = {"theme": "internal"}
    metadata = WorkflowMetadata(name="company_agent")
    requirements = WorkflowRequirements(provider_profiles=("default",), tools=("github.search_issues",), artifact_store=True)

    def build(*, context: object) -> object:
        build_calls.append("called")
        return {"context": context}

    workflow_definition = WorkflowDefinition(
        kind="company_agent",
        metadata=metadata,
        requirements=requirements,
        build=build,
        input_schema=input_schema,
        output_schema=output_schema,
        extra=extra,
    )

    assert workflow_definition.kind == "company_agent"
    assert workflow_definition.metadata is metadata
    assert workflow_definition.requirements is requirements
    assert workflow_definition.build is build
    assert workflow_definition.input_schema == input_schema
    assert workflow_definition.output_schema == output_schema
    assert workflow_definition.extra == extra
    assert workflow_definition.input_schema is not input_schema
    assert workflow_definition.output_schema is not output_schema
    assert workflow_definition.extra is not extra
    assert build_calls == []


def test_workflow_contribution_retains_definition_and_metadata() -> None:
    workflow_definition = WorkflowDefinition(
        kind="company_agent",
        metadata=WorkflowMetadata(name="company_agent"),
        requirements=WorkflowRequirements(),
        build=lambda **kwargs: object(),
    )
    metadata = {"owner": "platform"}

    contribution = WorkflowContribution(
        kind="company_agent",
        definition=workflow_definition,
        validate_config=lambda *args, **kwargs: None,
        metadata=metadata,
    )

    assert contribution.kind == "company_agent"
    assert contribution.definition is workflow_definition
    assert contribution.metadata == metadata
    assert contribution.metadata is not metadata
    assert callable(contribution.validate_config)
