from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
from django.test import override_settings

import langgraph_automation.apps.automation as automation_package
from langgraph_automation.api.errors import ArtifactPersistenceError, CheckpointPersistenceError, ConfigError
from langgraph_automation.apps.automation.apps import AutomationConfig
from langgraph_automation.apps.automation.models.run import Run, RunStatus
from langgraph_automation.apps.automation.models.workflow import Workflow
from langgraph_automation.apps.automation.services import runs as run_services
from langgraph_automation.apps.automation.services import runtime as runtime_module
from langgraph_automation.integrations.artifact.filesystem_store import FilesystemArtifactStore
from langgraph_automation.integrations.artifact.memory_store import MemoryArtifactStore
from langgraph_automation.integrations.checkpoint.filesystem_store import FilesystemCheckpointStore
from langgraph_automation.integrations.checkpoint.memory_store import MemoryCheckpointStore


def _app_config() -> AutomationConfig:
    return AutomationConfig("automation", automation_package)


def _workflow_payload() -> dict[str, object]:
    return {
        "llm": {"enabled": True, "model": "test-model"},
        "tools": {"allowed": ["echo"]},
    }


def _filesystem_settings(*, artifact_root: Path | None = None, checkpoint_root: Path | None = None) -> dict[str, object]:
    payload: dict[str, object] = {"version": 1}
    stores: dict[str, object] = {}
    if artifact_root is not None:
        stores["artifact"] = {"backend": "filesystem", "config": {"root": str(artifact_root)}}
    if checkpoint_root is not None:
        stores["checkpoint"] = {"backend": "filesystem", "config": {"root": str(checkpoint_root)}}
    if stores:
        payload["stores"] = stores
    return payload


def _deployment_json(payload: dict[str, object]) -> str:
    return json.dumps(payload)


@pytest.mark.django_db
def test_ready_binds_default_memory_services_and_reuses_them(monkeypatch: pytest.MonkeyPatch) -> None:
    app_config = _app_config()
    normalized_calls: list[object] = []
    original_normalizer = runtime_module.load_normalized_package_config_from_mapping

    def fake_normalizer(raw: object) -> object:
        normalized_calls.append(deepcopy(raw))
        return original_normalizer(raw)

    monkeypatch.setattr(runtime_module, "load_normalized_package_config_from_mapping", fake_normalizer)

    with override_settings(LANGGRAPH_AUTOMATION=_deployment_json({"version": 1})):
        app_config.ready()
        first_services = app_config.run_execution_services
        app_config.ready()

    workflow = Workflow.objects.create(
        name="wf-startup-default",
        definition_payload=_workflow_payload(),
    )
    run = Run.objects.create(workflow=workflow, name="run-startup-default")
    runtime = first_services.build_graph_runtime(run)

    assert normalized_calls == [{"version": 1}]
    assert app_config.run_execution_services is first_services
    assert isinstance(runtime.artifact_store, MemoryArtifactStore)
    assert isinstance(runtime.checkpoint_store, MemoryCheckpointStore)


@pytest.mark.django_db
@pytest.mark.parametrize(
    (
        "artifact_filesystem",
        "checkpoint_filesystem",
        "expected_artifact_cls",
        "expected_checkpoint_cls",
    ),
    [
        (False, False, MemoryArtifactStore, MemoryCheckpointStore),
        (True, False, FilesystemArtifactStore, MemoryCheckpointStore),
        (False, True, MemoryArtifactStore, FilesystemCheckpointStore),
        (True, True, FilesystemArtifactStore, FilesystemCheckpointStore),
    ],
)
def test_ready_binds_explicit_filesystem_selection_through_startup_path(
    artifact_filesystem: bool,
    checkpoint_filesystem: bool,
    expected_artifact_cls: type[object],
    expected_checkpoint_cls: type[object],
    tmp_path: Path,
) -> None:
    app_config = _app_config()
    workflow = Workflow.objects.create(
        name="wf-startup-filesystem",
        definition_payload=_workflow_payload(),
    )
    run = Run.objects.create(workflow=workflow, name="run-startup-filesystem")

    deployment_config: dict[str, object] = {"version": 1}
    if artifact_filesystem:
        artifact_root = tmp_path / "artifact-root"
        artifact_root.mkdir(parents=True)
        deployment_config.setdefault("stores", {})["artifact"] = {
            "backend": "filesystem",
            "config": {"root": str(artifact_root)},
        }
    if checkpoint_filesystem:
        checkpoint_root = tmp_path / "checkpoint-root"
        checkpoint_root.mkdir(parents=True)
        deployment_config.setdefault("stores", {})["checkpoint"] = {
            "backend": "filesystem",
            "config": {"root": str(checkpoint_root)},
        }

    with override_settings(LANGGRAPH_AUTOMATION=_deployment_json(deployment_config)):
        app_config.ready()
        runtime = app_config.run_execution_services.build_graph_runtime(run)

    assert isinstance(runtime.artifact_store, expected_artifact_cls)
    assert isinstance(runtime.checkpoint_store, expected_checkpoint_cls)
    if isinstance(runtime.artifact_store, FilesystemArtifactStore):
        assert runtime.artifact_store._root == Path(deployment_config["stores"]["artifact"]["config"]["root"])  # type: ignore[index]
    if isinstance(runtime.checkpoint_store, FilesystemCheckpointStore):
        assert runtime.checkpoint_store._root == Path(deployment_config["stores"]["checkpoint"]["config"]["root"])  # type: ignore[index]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "deployment_config",
    [
        _deployment_json(
            {
                "version": 1,
                "stores": {
                    "artifact": {
                        "backend": "filesystem",
                        "config": {},
                    }
                },
            }
        ),
        _deployment_json(
            {
                "version": 1,
                "stores": {
                    "artifact": {
                        "backend": "sqlite",
                    }
                },
            }
        ),
        _deployment_json(
            {
                "version": 1,
                "stores": {
                    "checkpoint": {
                        "backend": "filesystem",
                        "config": {"root": "relative/checkpoints"},
                    }
                },
            }
        ),
        json.dumps([]),
    ],
)
def test_ready_rejects_invalid_deployment_config_and_does_not_bind_services(deployment_config: str) -> None:
    app_config = _app_config()

    with override_settings(LANGGRAPH_AUTOMATION=deployment_config):
        with pytest.raises(ConfigError):
            app_config.ready()

    assert not hasattr(app_config, "run_execution_services")


@pytest.mark.django_db
def test_ready_is_idempotent_for_same_deployment_config_and_rejects_different_config() -> None:
    app_config = _app_config()

    with override_settings(LANGGRAPH_AUTOMATION=_deployment_json({"version": 1})):
        app_config.ready()
        first_services = app_config.run_execution_services
        app_config.ready()

    assert app_config.run_execution_services is first_services

    with override_settings(
        LANGGRAPH_AUTOMATION=_deployment_json(
            {
                "version": 1,
                "stores": {
                    "checkpoint": {
                        "backend": "filesystem",
                        "config": {"root": "/srv/langgraph-automation/checkpoints"},
                    }
                },
            }
        )
    ):
        with pytest.raises(ConfigError):
            app_config.ready()


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("deployment_config", "builder_name", "error_message"),
    [
        (
            _deployment_json(
                {
                    "version": 1,
                    "stores": {
                        "artifact": {
                            "backend": "filesystem",
                            "config": {"root": "/srv/langgraph-automation/artifacts"},
                        }
                    },
                }
            ),
            "build_package_artifact_store",
            "filesystem artifact store failed",
        ),
        (
            _deployment_json(
                {
                    "version": 1,
                    "stores": {
                        "checkpoint": {
                            "backend": "filesystem",
                            "config": {"root": "/srv/langgraph-automation/checkpoints"},
                        }
                    },
                }
            ),
            "build_package_checkpoint_store",
            "filesystem checkpoint store failed",
        ),
    ],
)
def test_ready_bound_filesystem_configuration_fails_closed_when_constructor_fails(
    deployment_config: str,
    builder_name: str,
    error_message: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app_config = _app_config()
    workflow = Workflow.objects.create(
        name="wf-startup-failure",
        definition_payload=_workflow_payload(),
    )
    run = Run.objects.create(workflow=workflow, name="run-startup-failure")
    artifact_builder_called = False
    checkpoint_builder_called = False

    def build_artifact_store(*_args, **_kwargs):
        nonlocal artifact_builder_called
        artifact_builder_called = True
        if builder_name == "build_package_artifact_store":
            raise ArtifactPersistenceError(
                error_message,
                code="ARTIFACT_PERSISTENCE_FAILURE",
                component="artifact_store",
            )
        return object()

    def build_checkpoint_store(*_args, **_kwargs):
        nonlocal checkpoint_builder_called
        checkpoint_builder_called = True
        if builder_name == "build_package_checkpoint_store":
            raise CheckpointPersistenceError(
                error_message,
                code="CHECKPOINT_PERSISTENCE_FAILURE",
                component="checkpoint_store",
            )
        raise AssertionError("checkpoint builder should not be called after artifact builder failure")

    monkeypatch.setattr(run_services, "dispatch_run_execution", lambda *_args, **_kwargs: pytest.fail("dispatch should not be called"))
    monkeypatch.setattr(runtime_module, "build_package_artifact_store", build_artifact_store)
    monkeypatch.setattr(runtime_module, "build_package_checkpoint_store", build_checkpoint_store)

    with override_settings(LANGGRAPH_AUTOMATION=deployment_config):
        app_config.ready()
        result = run_services.start_run(run=run, services=app_config.run_execution_services)

    run.refresh_from_db()
    assert run.status == RunStatus.FAILED
    assert result.run.status == RunStatus.FAILED
    assert result.execution_result is not None
    assert result.execution_result.status == RunStatus.FAILED
    assert result.message == "runtime configuration failed"
    assert result.execution_result.message == "runtime configuration failed"
    assert error_message in result.run.error_message
    assert error_message in result.execution_result.error_message
    assert result.output_payload == {}
    assert artifact_builder_called is True
    if builder_name == "build_package_artifact_store":
        assert checkpoint_builder_called is False
    else:
        assert checkpoint_builder_called is True
