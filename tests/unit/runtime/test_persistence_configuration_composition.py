"""Tests for composition-bound persistence configuration ownership."""

from __future__ import annotations

import pytest

from langgraph_automation.apps.automation.models.run import Run, RunStatus
from langgraph_automation.apps.automation.models.workflow import Workflow
from langgraph_automation.apps.automation.services import runs as run_services
from langgraph_automation.apps.automation.services import runtime as runtime_module
from langgraph_automation.config.normalizer import load_normalized_package_config_from_mapping
from langgraph_automation.graphs.runner import ExecutionResult


class _RecordingRuntimeFactory:
    def __init__(self, package_config: object) -> None:
        self.package_config = package_config
        self.calls: list[tuple[int, object]] = []

    def build_graph_runtime(self, run: Run) -> object:
        self.calls.append((run.pk, self.package_config))
        return object()


@pytest.mark.django_db
def test_build_run_execution_services_normalizes_trusted_config_once(monkeypatch: pytest.MonkeyPatch) -> None:
    normalized = load_normalized_package_config_from_mapping({"version": 1})
    calls: list[object] = []

    def fake_normalizer(raw: object) -> object:
        calls.append(raw)
        return normalized

    monkeypatch.setattr(runtime_module, 'load_normalized_package_config_from_mapping', fake_normalizer)

    services = runtime_module.build_run_execution_services_from_mapping({"version": 1})

    assert calls == [{"version": 1}]
    assert services.runtime_factory.package_config is normalized


@pytest.mark.django_db
def test_bound_run_execution_services_reuse_same_package_config_for_multiple_runs_and_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package_config = load_normalized_package_config_from_mapping({"version": 1})
    factory = _RecordingRuntimeFactory(package_config)
    services = runtime_module.RunExecutionServices(runtime_factory=factory)

    monkeypatch.setattr(
        run_services,
        'dispatch_run_execution',
        lambda *_args, **_kwargs: ExecutionResult(status=RunStatus.SUCCEEDED, output_payload={}, message='ok'),
    )

    workflow = Workflow.objects.create(
        name='wf-bound-composition',
        definition_payload={
            'llm': {'enabled': True, 'model': 'test-model'},
            'tools': {'allowed': ['echo']},
        },
    )
    first_run = Run.objects.create(workflow=workflow, name='run-bound-first')
    second_run = Run.objects.create(workflow=workflow, name='run-bound-second')
    retry_run = Run.objects.create(workflow=workflow, name='run-bound-retry', status=RunStatus.FAILED)

    run_services.start_run(run=first_run, services=services)
    run_services.start_run(run=second_run, services=services)
    run_services.retry_run(run=retry_run, services=services)

    assert factory.calls == [
        (first_run.pk, package_config),
        (second_run.pk, package_config),
        (retry_run.pk, package_config),
    ]
    assert services.runtime_factory.package_config is package_config
