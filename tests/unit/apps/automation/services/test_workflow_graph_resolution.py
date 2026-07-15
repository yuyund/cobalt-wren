"""Tests for graph resolution through the service bridge."""

from __future__ import annotations

import pytest

from langgraph_automation.api.engine import EnginePreparedWorkflow
from langgraph_automation.apps.automation.services.workflow_preparation import resolve_graph_for_run
from tests.support.engine_fixtures import create_reference_engine_config


def test_resolve_graph_for_run_returns_graph_object(monkeypatch: pytest.MonkeyPatch) -> None:
    sentinel_graph = object()

    class Prepared:
        graph = sentinel_graph

    calls: list[str] = []

    def fake_prepare_run_workflow(*, workflow_kind, config, plugins=()):
        calls.append(workflow_kind)
        assert config == create_reference_engine_config()
        assert plugins == ()
        return Prepared()

    monkeypatch.setattr(
        'langgraph_automation.apps.automation.services.workflow_preparation.prepare_run_workflow',
        fake_prepare_run_workflow,
    )

    graph = resolve_graph_for_run(workflow_kind='reference.llm_echo_summary', config=create_reference_engine_config())

    assert graph is sentinel_graph
    assert calls == ['reference.llm_echo_summary']


def test_resolve_graph_for_run_alias_works_end_to_end(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('OPENAI_API_KEY', 'test-key')
    graph = resolve_graph_for_run(workflow_kind='llm_echo_summary', config=create_reference_engine_config())

    assert graph is not None


def test_resolve_graph_for_run_uses_engine_prepared_workflow(monkeypatch: pytest.MonkeyPatch) -> None:
    sentinel_graph = object()

    def fake_prepare_run_workflow(*, workflow_kind, config, plugins=()):
        del config, plugins
        assert workflow_kind == 'reference.llm_echo_summary'
        return EnginePreparedWorkflow(kind=workflow_kind, graph=sentinel_graph)

    monkeypatch.setattr(
        'langgraph_automation.apps.automation.services.workflow_preparation.prepare_run_workflow',
        fake_prepare_run_workflow,
    )

    graph = resolve_graph_for_run(workflow_kind='reference.llm_echo_summary', config=create_reference_engine_config())

    assert graph is sentinel_graph
