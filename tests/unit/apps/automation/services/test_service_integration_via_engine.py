"""Service-facing integration tests through the engine facade."""

from __future__ import annotations

import pytest

from langgraph_automation.api.engine import EnginePreparedWorkflow
from langgraph_automation.apps.automation.services.workflow_preparation import prepare_run_workflow, resolve_graph_for_run
from tests.support.engine_fixtures import create_reference_engine_config


def test_service_layer_prepares_reference_workflow_through_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('OPENAI_API_KEY', 'test-key')

    prepared = prepare_run_workflow(
        workflow_kind='reference.llm_echo_summary',
        config=create_reference_engine_config(),
    )

    assert isinstance(prepared, EnginePreparedWorkflow)
    assert prepared.kind == 'reference.llm_echo_summary'
    assert prepared.graph is not None


def test_service_layer_canonicalizes_legacy_workflow_kind(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('OPENAI_API_KEY', 'test-key')

    prepared = prepare_run_workflow(
        workflow_kind='llm_echo_summary',
        config=create_reference_engine_config(),
    )

    assert prepared.kind == 'reference.llm_echo_summary'
    assert prepared.graph is not None


def test_service_layer_resolve_graph_returns_opaque_graph(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('OPENAI_API_KEY', 'test-key')

    graph = resolve_graph_for_run(
        workflow_kind='reference.llm_echo_summary',
        config=create_reference_engine_config(),
    )

    assert graph is not None
