"""Tests for the internal workflow requirements checker."""

from __future__ import annotations

import pytest

from cobalt_wren.api.errors import RuntimeAssemblyError
from cobalt_wren.api.workflow import WorkflowRequirements
from cobalt_wren.runtime.dependencies import RuntimeDependencies
from cobalt_wren.workflows.requirements import check_workflow_requirements


def _dependencies() -> RuntimeDependencies:
    return RuntimeDependencies(
        providers={'default': object()},
        tools={'echo': object()},
        artifact_store=object(),
        checkpoint_store=object(),
        event_sinks={'stdout': object()},
    )


def test_check_workflow_requirements_accepts_complete_runtime_dependencies() -> None:
    requirements = WorkflowRequirements(
        provider_profiles=('default',),
        tools=('echo',),
        artifact_store=True,
        checkpoint_store=True,
        event_sinks=('stdout',),
    )

    check_workflow_requirements(requirements, _dependencies())


def test_check_workflow_requirements_accepts_empty_requirements() -> None:
    check_workflow_requirements(WorkflowRequirements(), RuntimeDependencies(providers={}, tools={}))


def test_check_workflow_requirements_rejects_missing_provider_profile() -> None:
    requirements = WorkflowRequirements(provider_profiles=('missing',))

    with pytest.raises(RuntimeAssemblyError) as excinfo:
        check_workflow_requirements(requirements, RuntimeDependencies(providers={}, tools={}))

    assert excinfo.value.code == 'WORKFLOW_REQUIREMENT_MISSING'
    assert excinfo.value.metadata['requirement_type'] == 'provider_profile'


def test_check_workflow_requirements_rejects_missing_tool() -> None:
    requirements = WorkflowRequirements(tools=('missing.tool',))

    with pytest.raises(RuntimeAssemblyError) as excinfo:
        check_workflow_requirements(requirements, RuntimeDependencies(providers={}, tools={}))

    assert excinfo.value.metadata['requirement_type'] == 'tool'
    assert excinfo.value.metadata['requirement_name'] == 'missing.tool'


def test_check_workflow_requirements_rejects_missing_artifact_store() -> None:
    requirements = WorkflowRequirements(artifact_store=True)

    with pytest.raises(RuntimeAssemblyError) as excinfo:
        check_workflow_requirements(requirements, RuntimeDependencies(providers={}, tools={}))

    assert excinfo.value.metadata['requirement_type'] == 'artifact_store'


def test_check_workflow_requirements_rejects_missing_checkpoint_store() -> None:
    requirements = WorkflowRequirements(checkpoint_store=True)

    with pytest.raises(RuntimeAssemblyError) as excinfo:
        check_workflow_requirements(requirements, RuntimeDependencies(providers={}, tools={}))

    assert excinfo.value.metadata['requirement_type'] == 'checkpoint_store'


def test_check_workflow_requirements_rejects_missing_event_sink() -> None:
    requirements = WorkflowRequirements(event_sinks=('missing',))

    with pytest.raises(RuntimeAssemblyError) as excinfo:
        check_workflow_requirements(requirements, RuntimeDependencies(providers={}, tools={}))

    assert excinfo.value.metadata['requirement_type'] == 'event_sink'
    assert excinfo.value.metadata['requirement_name'] == 'missing'
