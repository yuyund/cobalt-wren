"""Tests for the control-plane workflow preparation bridge."""

from __future__ import annotations

import pytest

from langgraph_automation.api.engine import EnginePreparedWorkflow
from langgraph_automation.api.errors import PluginResolutionError, RuntimeAssemblyError
from langgraph_automation.apps.automation.services.workflow_preparation import (
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
    assert prepared.executable is not None
    assert type(prepared).__name__ == 'EnginePreparedWorkflow'


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
