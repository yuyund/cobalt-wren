"""Tests for the control-plane workflow preparation bridge."""

from __future__ import annotations

import pytest

from cobalt_wren.api.engine import EnginePreparedWorkflow
from cobalt_wren.api.errors import PluginResolutionError, RuntimeAssemblyError
from cobalt_wren.apps.automation.services.workflow_preparation import (
    prepare_run_workflow,
)
from tests.support.engine_fixtures import create_reference_engine_config
from tests.support.native_workflow_fixtures import (
    TEST_REQUIRED_WORKFLOW_KIND,
    create_required_native_plugin,
)


def test_prepare_run_workflow_returns_public_engine_handle(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('OPENAI_API_KEY', 'test-key')

    prepared = prepare_run_workflow(
        workflow_kind=TEST_REQUIRED_WORKFLOW_KIND,
        config=create_reference_engine_config(),
        plugins=(create_required_native_plugin(),),
    )

    assert isinstance(prepared, EnginePreparedWorkflow)
    assert prepared.kind == TEST_REQUIRED_WORKFLOW_KIND
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
        prepare_run_workflow(
            workflow_kind=TEST_REQUIRED_WORKFLOW_KIND,
            config={'version': 1, 'environment': 'test'},
            plugins=(create_required_native_plugin(),),
        )

    assert excinfo.value.code == 'WORKFLOW_REQUIREMENT_MISSING'
