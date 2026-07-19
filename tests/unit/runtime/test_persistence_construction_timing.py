"""Construction timing tests for persistence startup and runtime assembly."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
from django.test import override_settings

import langgraph_automation.apps.automation as automation_package
from langgraph_automation.apps.automation.apps import AutomationConfig
from langgraph_automation.apps.automation.models.run import Run, RunStatus
from langgraph_automation.apps.automation.models.workflow import Workflow
from langgraph_automation.apps.automation.services import runs as run_services
from langgraph_automation.apps.automation.services import runtime as runtime_module
from langgraph_automation.config.artifact_store import normalize_artifact_store_settings
from langgraph_automation.config.models import NormalizedPackageConfig
from langgraph_automation.graphs.runner import ExecutionResult
from langgraph_automation.runtime import assembly as runtime_assembly


def _app_config() -> AutomationConfig:
    return AutomationConfig("automation", automation_package)


def _deployment_json(payload: dict[str, object]) -> str:
    return json.dumps(payload)


def _workflow_payload() -> dict[str, object]:
    return {
        "llm": {"enabled": True, "model": "test-model"},
        "tools": {"allowed": ["echo"]},
    }


@pytest.mark.django_db
def test_ready_normalizes_once_and_defers_store_construction(monkeypatch: pytest.MonkeyPatch) -> None:
    app_config = _app_config()
    loader_calls: list[object] = []
    normalizer_calls: list[object] = []
    artifact_builder_calls: list[object] = []
    checkpoint_builder_calls: list[object] = []
    assemble_calls: list[object] = []

    original_loader = runtime_module.load_deployment_package_config_from_settings
    original_normalizer = runtime_module.load_normalized_package_config_from_mapping

    def fake_loader() -> object:
        value = original_loader()
        loader_calls.append(deepcopy(value))
        return value

    def fake_normalizer(raw: object) -> object:
        normalizer_calls.append(deepcopy(raw))
        return original_normalizer(raw)

    def fail_artifact_builder(*_args, **_kwargs) -> object:
        artifact_builder_calls.append(object())
        raise AssertionError("ready() should not construct artifact stores")

    def fail_checkpoint_builder(*_args, **_kwargs) -> object:
        checkpoint_builder_calls.append(object())
        raise AssertionError("ready() should not construct checkpoint stores")

    def fail_assemble(self: object, config: object) -> object:
        assemble_calls.append(config)
        raise AssertionError("ready() should not assemble runtime dependencies")

    monkeypatch.setattr(runtime_module, "load_deployment_package_config_from_settings", fake_loader)
    monkeypatch.setattr(runtime_module, "load_normalized_package_config_from_mapping", fake_normalizer)
    monkeypatch.setattr(runtime_module, "build_package_artifact_store", fail_artifact_builder)
    monkeypatch.setattr(runtime_module, "build_package_checkpoint_store", fail_checkpoint_builder)
    monkeypatch.setattr(runtime_assembly.RuntimeAssembler, "assemble", fail_assemble)

    with override_settings(LANGGRAPH_AUTOMATION=_deployment_json({"version": 1})):
        app_config.ready()
        services = app_config.run_execution_services

    assert loader_calls == [{"version": 1}]
    assert normalizer_calls == [{"version": 1}]
    assert isinstance(services.runtime_factory.package_config, NormalizedPackageConfig)
    assert artifact_builder_calls == []
    assert checkpoint_builder_calls == []
    assert assemble_calls == []


@pytest.mark.django_db
def test_runtime_builds_stores_once_per_run_and_reuses_bound_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    app_config = _app_config()
    artifact_settings_seen: list[object] = []
    checkpoint_settings_seen: list[object] = []
    artifact_stores: list[object] = []
    checkpoint_stores: list[object] = []
    runtime_inputs: list[object] = []
    normalizer_calls: list[object] = []
    assemble_calls: list[object] = []

    original_normalizer = runtime_module.load_normalized_package_config_from_mapping

    def fake_normalizer(raw: object) -> object:
        normalizer_calls.append(deepcopy(raw))
        return original_normalizer(raw)

    def fake_build_artifact_store(settings: object) -> object:
        artifact_settings_seen.append(settings)
        store = object()
        artifact_stores.append(store)
        return store

    def fake_build_checkpoint_store(settings: object) -> object:
        checkpoint_settings_seen.append(settings)
        store = object()
        checkpoint_stores.append(store)
        return store

    def fail_assemble(self: object, config: object) -> object:
        assemble_calls.append(config)
        raise AssertionError("run execution path should not assemble runtime dependencies directly")

    def fake_dispatch_run_execution(run: Run, *, runtime: object) -> ExecutionResult:
        runtime_inputs.append(runtime)
        return ExecutionResult(status=RunStatus.SUCCEEDED, output_payload={}, message="ok")

    monkeypatch.setattr(runtime_module, "load_normalized_package_config_from_mapping", fake_normalizer)
    monkeypatch.setattr(runtime_module, "build_package_artifact_store", fake_build_artifact_store)
    monkeypatch.setattr(runtime_module, "build_package_checkpoint_store", fake_build_checkpoint_store)
    monkeypatch.setattr(runtime_assembly.RuntimeAssembler, "assemble", fail_assemble)
    monkeypatch.setattr(run_services, "dispatch_run_execution", fake_dispatch_run_execution)

    deployment_config = {
        "version": 1,
        "stores": {
            "artifact": {
                "backend": "filesystem",
                "config": {"root": str(tmp_path / "artifacts")},
            },
            "checkpoint": {
                "backend": "filesystem",
                "config": {"root": str(tmp_path / "checkpoints")},
            },
        },
    }

    with override_settings(LANGGRAPH_AUTOMATION=_deployment_json(deployment_config)):
        app_config.ready()
        services = app_config.run_execution_services

    workflow = Workflow.objects.create(name="wf-construction-timing", definition_payload=_workflow_payload())
    first_run = Run.objects.create(workflow=workflow, name="run-construction-first")
    second_run = Run.objects.create(workflow=workflow, name="run-construction-second")
    retry_run = Run.objects.create(workflow=workflow, name="run-construction-retry", status=RunStatus.FAILED)

    first_result = run_services.start_run(run=first_run, services=services)
    second_result = run_services.start_run(run=second_run, services=services)
    retry_result = run_services.retry_run(run=retry_run, services=services)

    assert first_result.run.status == RunStatus.SUCCEEDED
    assert second_result.run.status == RunStatus.SUCCEEDED
    assert retry_result.run.status == RunStatus.SUCCEEDED
    assert normalizer_calls == [deployment_config]
    expected_artifact_settings = normalize_artifact_store_settings(
        services.runtime_factory.package_config.stores["artifact"]
    )
    assert artifact_settings_seen == [expected_artifact_settings, expected_artifact_settings, expected_artifact_settings]
    assert checkpoint_settings_seen == [
        services.runtime_factory.package_config.checkpoint_store,
        services.runtime_factory.package_config.checkpoint_store,
        services.runtime_factory.package_config.checkpoint_store,
    ]
    assert len(artifact_stores) == 3
    assert len(checkpoint_stores) == 3
    assert runtime_inputs[0].artifact_store is artifact_stores[0]
    assert runtime_inputs[0].checkpoint_store is checkpoint_stores[0]
    assert runtime_inputs[1].artifact_store is artifact_stores[1]
    assert runtime_inputs[1].checkpoint_store is checkpoint_stores[1]
    assert runtime_inputs[2].artifact_store is artifact_stores[2]
    assert runtime_inputs[2].checkpoint_store is checkpoint_stores[2]
    assert runtime_inputs[0].artifact_store is not runtime_inputs[1].artifact_store
    assert runtime_inputs[0].checkpoint_store is not runtime_inputs[1].checkpoint_store
    assert runtime_inputs[1].artifact_store is not runtime_inputs[2].artifact_store
    assert runtime_inputs[1].checkpoint_store is not runtime_inputs[2].checkpoint_store
    assert assemble_calls == []
