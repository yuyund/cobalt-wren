"""Tests for graph resolution through the service bridge."""

from __future__ import annotations

from langgraph_automation.apps.automation.services.workflow_preparation import resolve_graph_for_run
from langgraph_automation.plugins.registry import PluginRegistry
from langgraph_automation.runtime.dependencies import RuntimeDependencies


def _dependencies() -> RuntimeDependencies:
    return RuntimeDependencies(
        providers={'default': object()},
        tools={'echo': object()},
        artifact_store=None,
        checkpoint_store=None,
        event_sinks={},
    )


def test_resolve_graph_for_run_returns_graph_object(monkeypatch) -> None:
    sentinel_graph = object()

    class Prepared:
        graph = sentinel_graph

    calls: list[str] = []

    def fake_prepare_run_workflow(*, workflow_kind, dependencies, registry=None):
        calls.append(workflow_kind)
        return Prepared()

    monkeypatch.setattr(
        'langgraph_automation.apps.automation.services.workflow_preparation.prepare_run_workflow',
        fake_prepare_run_workflow,
    )

    graph = resolve_graph_for_run(workflow_kind='reference.llm_echo_summary', dependencies=_dependencies(), registry=PluginRegistry())

    assert graph is sentinel_graph
    assert calls == ['reference.llm_echo_summary']


def test_resolve_graph_for_run_alias_works_end_to_end() -> None:
    graph = resolve_graph_for_run(workflow_kind='llm_echo_summary', dependencies=_dependencies())

    assert graph is not None
