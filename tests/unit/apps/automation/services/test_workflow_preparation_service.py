"""Tests for the control-plane workflow preparation bridge."""

from __future__ import annotations

import pytest

from langgraph_automation.api.engine import EnginePreparedWorkflow
from langgraph_automation.api.errors import PluginResolutionError, RuntimeAssemblyError
from langgraph_automation.apps.automation.services.workflow_preparation import (
    CANONICAL_REFERENCE_WORKFLOW_KIND,
    canonicalize_workflow_kind,
    prepare_run_workflow,
)
from tests.support.engine_fixtures import create_reference_engine_config


def test_prepare_run_workflow_returns_public_engine_handle(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('OPENAI_API_KEY', 'test-key')

    prepared = prepare_run_workflow(
        workflow_kind='reference.llm_echo_summary',
        config=create_reference_engine_config(),
    )

    assert isinstance(prepared, EnginePreparedWorkflow)
    assert prepared.kind == 'reference.llm_echo_summary'
    assert prepared.graph is not None
    assert type(prepared).__name__ == 'EnginePreparedWorkflow'


def test_prepare_run_workflow_applies_compatibility_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('OPENAI_API_KEY', 'test-key')

    prepared = prepare_run_workflow(
        workflow_kind='llm_echo_summary',
        config=create_reference_engine_config(),
    )

    assert canonicalize_workflow_kind('llm_echo_summary') == CANONICAL_REFERENCE_WORKFLOW_KIND
    assert prepared.kind == CANONICAL_REFERENCE_WORKFLOW_KIND


def test_prepare_run_workflow_rejects_unknown_workflow_kind(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('OPENAI_API_KEY', 'test-key')
    with pytest.raises(PluginResolutionError) as excinfo:
        prepare_run_workflow(workflow_kind='missing.workflow', config=create_reference_engine_config())

    assert excinfo.value.component == 'workflow_preparer'
    assert excinfo.value.metadata['workflow_kind'] == 'missing.workflow'


def test_prepare_run_workflow_rejects_missing_requirements() -> None:
    with pytest.raises(RuntimeAssemblyError) as excinfo:
        prepare_run_workflow(workflow_kind='reference.llm_echo_summary', config={'version': 1, 'environment': 'test'})

    assert excinfo.value.code == 'WORKFLOW_REQUIREMENT_MISSING'


def test_prepare_run_workflow_uses_api_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, tuple[str, ...]]] = []

    class FakeEngine:
        def prepare_workflow(self, workflow_kind: str) -> EnginePreparedWorkflow:
            calls.append((workflow_kind, ()))
            return EnginePreparedWorkflow(kind=workflow_kind, graph={'graph': 'sentinel'})

    def fake_create_engine(config, *, plugins=()):
        assert config == create_reference_engine_config()
        assert isinstance(plugins, tuple)
        return FakeEngine()

    monkeypatch.setattr('langgraph_automation.apps.automation.services.workflow_preparation.create_engine', fake_create_engine)

    prepared = prepare_run_workflow(
        workflow_kind='llm_echo_summary',
        config=create_reference_engine_config(),
    )

    assert prepared.kind == CANONICAL_REFERENCE_WORKFLOW_KIND
    assert prepared.graph == {'graph': 'sentinel'}
    assert calls == [(CANONICAL_REFERENCE_WORKFLOW_KIND, ())]
