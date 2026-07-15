"""Tests for the control-plane workflow preparation bridge."""

from __future__ import annotations

import pytest

from langgraph_automation.api.errors import PluginResolutionError, RuntimeAssemblyError
from langgraph_automation.api.plugins import Plugin, PluginContributions, PluginMetadata
from langgraph_automation.api.workflow import WorkflowContribution, WorkflowDefinition, WorkflowMetadata, WorkflowRequirements
from langgraph_automation.apps.automation.services.workflow_preparation import (
    CANONICAL_REFERENCE_WORKFLOW_KIND,
    canonicalize_workflow_kind,
    prepare_run_workflow,
)
from langgraph_automation.plugins.registry import PluginRegistry
from langgraph_automation.runtime.dependencies import RuntimeDependencies
from langgraph_automation.workflows.catalog import create_builtin_workflow_registry


def _dependencies() -> RuntimeDependencies:
    return RuntimeDependencies(
        providers={'default': object()},
        tools={'echo': object()},
        artifact_store=None,
        checkpoint_store=None,
        event_sinks={},
    )


def _workflow_registry(*, validate_calls: list[str] | None = None) -> PluginRegistry:
    registry = PluginRegistry()

    def validate_config(*args, **kwargs):
        if validate_calls is not None:
            validate_calls.append('validate')
        raise AssertionError('validate_config should not be called during preparation')

    contribution = WorkflowContribution(
        kind='test.workflow',
        definition=WorkflowDefinition(
            kind='test.workflow',
            metadata=WorkflowMetadata(name='Test Workflow'),
            requirements=WorkflowRequirements(provider_profiles=('default',), tools=('echo',)),
            build=lambda: {'graph': 'built'},
        ),
        validate_config=validate_config,
    )
    registry.register(
        Plugin(
            metadata=PluginMetadata(name='test-workflow-plugin', version='0.1.0', plugin_types=('workflow',)),
            contributions=PluginContributions(workflows=(contribution,)),
        )
    )
    return registry


def test_prepare_run_workflow_uses_builtin_registry_by_default() -> None:
    prepared = prepare_run_workflow(workflow_kind='reference.llm_echo_summary', dependencies=_dependencies())

    assert prepared.kind == 'reference.llm_echo_summary'
    assert prepared.definition.kind == 'reference.llm_echo_summary'
    assert prepared.graph is not None


def test_prepare_run_workflow_uses_injected_registry() -> None:
    registry = _workflow_registry()

    prepared = prepare_run_workflow(workflow_kind='test.workflow', dependencies=_dependencies(), registry=registry)

    assert prepared.kind == 'test.workflow'
    assert prepared.definition.kind == 'test.workflow'
    assert prepared.graph is not None


def test_prepare_run_workflow_applies_compatibility_alias() -> None:
    prepared = prepare_run_workflow(workflow_kind='llm_echo_summary', dependencies=_dependencies())

    assert canonicalize_workflow_kind('llm_echo_summary') == CANONICAL_REFERENCE_WORKFLOW_KIND
    assert prepared.kind == CANONICAL_REFERENCE_WORKFLOW_KIND
    assert prepared.definition.kind == CANONICAL_REFERENCE_WORKFLOW_KIND


def test_prepare_run_workflow_rejects_unknown_workflow_kind() -> None:
    with pytest.raises(PluginResolutionError) as excinfo:
        prepare_run_workflow(workflow_kind='missing.workflow', dependencies=_dependencies(), registry=PluginRegistry())

    assert excinfo.value.component == 'workflow_preparer'
    assert excinfo.value.metadata['workflow_kind'] == 'missing.workflow'


def test_prepare_run_workflow_rejects_missing_requirements() -> None:
    registry = create_builtin_workflow_registry()

    with pytest.raises(RuntimeAssemblyError) as excinfo:
        prepare_run_workflow(
            workflow_kind='reference.llm_echo_summary',
            dependencies=RuntimeDependencies(providers={}, tools={}, artifact_store=None, checkpoint_store=None, event_sinks={}),
            registry=registry,
        )

    assert excinfo.value.code == 'WORKFLOW_REQUIREMENT_MISSING'


def test_prepare_run_workflow_does_not_call_validate_config() -> None:
    validate_calls: list[str] = []
    registry = _workflow_registry(validate_calls=validate_calls)
    prepared = prepare_run_workflow(workflow_kind='test.workflow', dependencies=_dependencies(), registry=registry)

    assert prepared.kind == 'test.workflow'
    assert validate_calls == []
