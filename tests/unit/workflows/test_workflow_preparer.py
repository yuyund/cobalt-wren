"""Tests for the workflow preparation path."""

from __future__ import annotations

import pytest

from langgraph_automation.api.errors import PluginResolutionError, RuntimeAssemblyError
from langgraph_automation.plugins.registry import PluginRegistry
from langgraph_automation.runtime.dependencies import RuntimeDependencies
from langgraph_automation.workflows.catalog import create_builtin_workflow_registry
from langgraph_automation.workflows.prepare import PreparedWorkflow, WorkflowPreparer, prepare_workflow


def _runtime_dependencies() -> RuntimeDependencies:
    return RuntimeDependencies(
        providers={'default': object()},
        tools={'echo': object()},
        artifact_store=None,
        checkpoint_store=None,
        event_sinks={},
    )


def test_workflow_preparer_prepares_registered_workflow(monkeypatch: pytest.MonkeyPatch) -> None:
    registry = PluginRegistry()
    contribution_calls: list[str] = []

    from langgraph_automation.api.plugins import Plugin, PluginContributions, PluginMetadata
    from langgraph_automation.api.workflow import WorkflowContribution, WorkflowDefinition, WorkflowMetadata, WorkflowRequirements

    def _validate(*args, **kwargs):
        contribution_calls.append('validate')
        raise AssertionError('validate_config should not be called during preparation')

    definition = WorkflowDefinition(
        kind='sample.workflow',
        metadata=WorkflowMetadata(name='Sample Workflow'),
        requirements=WorkflowRequirements(provider_profiles=('default',), tools=('echo',)),
        build=lambda: {'graph': 'built'},
    )
    contribution = WorkflowContribution(kind='sample.workflow', definition=definition, validate_config=_validate)
    registry.register(
        Plugin(
            metadata=PluginMetadata(name='sample-plugin', version='0.1.0', plugin_types=('workflow',)),
            contributions=PluginContributions(workflows=(contribution,)),
        )
    )

    build_calls: list[str] = []

    def fake_build_workflow_graph(definition_arg):
        build_calls.append(definition_arg.kind)
        return {'prepared': definition_arg.kind}

    monkeypatch.setattr('langgraph_automation.workflows.prepare.build_workflow_graph', fake_build_workflow_graph)

    prepared = WorkflowPreparer(registry).prepare(workflow_kind='sample.workflow', dependencies=_runtime_dependencies())

    assert isinstance(prepared, PreparedWorkflow)
    assert prepared.kind == 'sample.workflow'
    assert prepared.contribution is contribution
    assert prepared.definition is definition
    assert prepared.graph == {'prepared': 'sample.workflow'}
    assert build_calls == ['sample.workflow']
    assert contribution_calls == []


def test_workflow_preparer_wraps_unknown_workflow_kind() -> None:
    registry = PluginRegistry()

    with pytest.raises(PluginResolutionError) as excinfo:
        WorkflowPreparer(registry).prepare(workflow_kind='missing.workflow', dependencies=_runtime_dependencies())

    assert excinfo.value.code == 'WORKFLOW_PREPARATION_WORKFLOW_NOT_FOUND'
    assert excinfo.value.component == 'workflow_preparer'
    assert excinfo.value.metadata['workflow_kind'] == 'missing.workflow'


def test_workflow_preparer_raises_for_missing_requirements() -> None:
    registry = create_builtin_workflow_registry()

    with pytest.raises(RuntimeAssemblyError) as excinfo:
        WorkflowPreparer(registry).prepare(
            workflow_kind='reference.llm_echo_summary',
            dependencies=RuntimeDependencies(providers={}, tools={}, artifact_store=None, checkpoint_store=None, event_sinks={}),
        )

    assert excinfo.value.code == 'WORKFLOW_REQUIREMENT_MISSING'


def test_prepare_workflow_helper_prepares_builtin_workflow() -> None:
    prepared = prepare_workflow(
        workflow_kind='reference.llm_echo_summary',
        registry=create_builtin_workflow_registry(),
        dependencies=_runtime_dependencies(),
    )

    assert prepared.kind == 'reference.llm_echo_summary'
    assert prepared.definition.kind == 'reference.llm_echo_summary'
    assert prepared.graph is not None
