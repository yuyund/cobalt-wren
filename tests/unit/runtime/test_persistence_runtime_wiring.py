"""Runtime wiring regressions for persistence backends."""

from __future__ import annotations

from pathlib import Path

import pytest

from langgraph_automation.apps.automation.models.run import Run
from langgraph_automation.apps.automation.models.workflow import Workflow
from langgraph_automation.apps.automation.services.runtime import build_graph_runtime
from langgraph_automation.config.models import FilesystemArtifactStoreSettings, FilesystemCheckpointStoreSettings
from langgraph_automation.integrations.artifact.filesystem_store import FilesystemArtifactStore
from langgraph_automation.integrations.artifact.memory_store import MemoryArtifactStore
from langgraph_automation.integrations.checkpoint.filesystem_store import FilesystemCheckpointStore
from langgraph_automation.integrations.checkpoint.memory_store import MemoryCheckpointStore
from tests.support.persistence import DurabilityLevel, artifact_backend_specs, checkpoint_backend_specs


def _workflow_payload(
    *,
    artifact_store: dict[str, object] | None = None,
    checkpoint_store: dict[str, object] | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {'llm': {'enabled': True, 'model': 'test-model'}, 'tools': {'allowed': []}}
    stores: dict[str, object] = {}
    if artifact_store is not None:
        stores['artifact'] = artifact_store
    if checkpoint_store is not None:
        stores['checkpoint'] = checkpoint_store
    if stores:
        payload['stores'] = stores
    return payload


@pytest.mark.django_db
def test_runtime_wires_ephemeral_memory_persistence_backends() -> None:
    workflow = Workflow.objects.create(
        name='wf-persistence-runtime',
        definition_payload=_workflow_payload(),
    )
    run = Run.objects.create(workflow=workflow, name='run-persistence-runtime')

    runtime = build_graph_runtime(run)

    assert isinstance(runtime.artifact_store, MemoryArtifactStore)
    assert isinstance(runtime.checkpoint_store, MemoryCheckpointStore)
    assert artifact_backend_specs()[0].durability == DurabilityLevel.EPHEMERAL
    assert {spec.name for spec in artifact_backend_specs()} == {'memory', 'filesystem'}
    assert checkpoint_backend_specs()[0].durability == DurabilityLevel.EPHEMERAL
    assert runtime.artifact_store is not None
    assert runtime.checkpoint_store is not None


@pytest.mark.django_db
def test_runtime_wires_explicit_filesystem_artifact_and_memory_checkpoint_backends(tmp_path: Path) -> None:
    artifact_root = tmp_path / 'artifacts'
    workflow = Workflow.objects.create(
        name='wf-persistence-artifact-filesystem',
        definition_payload=_workflow_payload(
            artifact_store={'backend': 'filesystem', 'config': {'root': str(artifact_root)}},
            checkpoint_store={'backend': 'memory'},
        ),
    )
    run = Run.objects.create(workflow=workflow, name='run-persistence-artifact-filesystem')

    runtime = build_graph_runtime(run)

    assert isinstance(runtime.artifact_store, FilesystemArtifactStore)
    assert isinstance(runtime.checkpoint_store, MemoryCheckpointStore)
    assert runtime.artifact_store._root == artifact_root  # type: ignore[attr-defined]


@pytest.mark.django_db
def test_runtime_wires_memory_artifact_and_explicit_filesystem_checkpoint_backends(tmp_path: Path) -> None:
    checkpoint_root = tmp_path / 'checkpoints'
    workflow = Workflow.objects.create(
        name='wf-persistence-checkpoint-filesystem',
        definition_payload=_workflow_payload(
            artifact_store={'backend': 'memory'},
            checkpoint_store={'backend': 'filesystem', 'config': {'root': str(checkpoint_root)}},
        ),
    )
    run = Run.objects.create(workflow=workflow, name='run-persistence-checkpoint-filesystem')

    runtime = build_graph_runtime(run)

    assert isinstance(runtime.artifact_store, MemoryArtifactStore)
    assert isinstance(runtime.checkpoint_store, FilesystemCheckpointStore)
    assert runtime.checkpoint_store._root == checkpoint_root  # type: ignore[attr-defined]


@pytest.mark.django_db
def test_runtime_wires_explicit_filesystem_artifact_and_checkpoint_backends_with_distinct_roots(tmp_path: Path) -> None:
    artifact_root = tmp_path / 'artifacts'
    checkpoint_root = tmp_path / 'checkpoints'
    workflow = Workflow.objects.create(
        name='wf-persistence-filesystem-both',
        definition_payload=_workflow_payload(
            artifact_store={'backend': 'filesystem', 'config': {'root': str(artifact_root)}},
            checkpoint_store={'backend': 'filesystem', 'config': {'root': str(checkpoint_root)}},
        ),
    )
    run = Run.objects.create(workflow=workflow, name='run-persistence-filesystem-both')

    runtime = build_graph_runtime(run)

    assert isinstance(runtime.artifact_store, FilesystemArtifactStore)
    assert isinstance(runtime.checkpoint_store, FilesystemCheckpointStore)
    assert runtime.artifact_store._root == artifact_root  # type: ignore[attr-defined]
    assert runtime.checkpoint_store._root == checkpoint_root  # type: ignore[attr-defined]
    assert runtime.artifact_store._root != runtime.checkpoint_store._root  # type: ignore[attr-defined]


@pytest.mark.django_db
def test_runtime_preserves_selected_store_instances(monkeypatch: pytest.MonkeyPatch) -> None:
    artifact_store = object()
    checkpoint_store = object()
    calls: list[tuple[str, object]] = []

    def fake_build_artifact_store(settings: object) -> object:
        calls.append(("artifact", settings))
        return artifact_store

    def fake_build_checkpoint_store(settings: object) -> object:
        calls.append(("checkpoint", settings))
        return checkpoint_store

    monkeypatch.setattr(
        "langgraph_automation.apps.automation.services.runtime.build_package_artifact_store",
        fake_build_artifact_store,
    )
    monkeypatch.setattr(
        "langgraph_automation.apps.automation.services.runtime.build_package_checkpoint_store",
        fake_build_checkpoint_store,
    )

    workflow = Workflow.objects.create(
        name='wf-persistence-selected-instances',
        definition_payload=_workflow_payload(
            artifact_store={'backend': 'filesystem', 'config': {'root': '/srv/langgraph-automation/artifacts'}},
            checkpoint_store={'backend': 'filesystem', 'config': {'root': '/srv/langgraph-automation/checkpoints'}},
        ),
    )
    run = Run.objects.create(workflow=workflow, name='run-persistence-selected-instances')

    runtime = build_graph_runtime(run)

    assert runtime.artifact_store is artifact_store
    assert runtime.checkpoint_store is checkpoint_store
    assert calls == [
        (
            'artifact',
            FilesystemArtifactStoreSettings(
                backend='filesystem',
                root=Path('/srv/langgraph-automation/artifacts'),
            ),
        ),
        (
            'checkpoint',
            FilesystemCheckpointStoreSettings(
                backend='filesystem',
                root=Path('/srv/langgraph-automation/checkpoints'),
            ),
        ),
    ]


@pytest.mark.django_db
def test_runtime_does_not_fallback_to_memory_when_artifact_builder_fails(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[str] = []

    def fail_build_artifact_store(settings: object) -> object:
        calls.append("artifact")
        raise RuntimeError("filesystem artifact store failed")

    def fail_if_checkpoint_built(settings: object) -> object:
        calls.append("checkpoint")
        raise AssertionError("checkpoint builder should not be reached after artifact failure")

    monkeypatch.setattr(
        "langgraph_automation.apps.automation.services.runtime.build_package_artifact_store",
        fail_build_artifact_store,
    )
    monkeypatch.setattr(
        "langgraph_automation.apps.automation.services.runtime.build_package_checkpoint_store",
        fail_if_checkpoint_built,
    )

    workflow = Workflow.objects.create(
        name='wf-persistence-artifact-failure',
        definition_payload=_workflow_payload(
            artifact_store={'backend': 'filesystem', 'config': {'root': str(tmp_path / 'artifacts')}},
            checkpoint_store={'backend': 'memory'},
        ),
    )
    run = Run.objects.create(workflow=workflow, name='run-persistence-artifact-failure')

    with pytest.raises(RuntimeError, match='filesystem artifact store failed'):
        build_graph_runtime(run)

    assert calls == ['artifact']


@pytest.mark.django_db
def test_runtime_does_not_fallback_to_memory_when_checkpoint_builder_fails(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[str] = []

    def build_artifact_store(settings: object) -> object:
        calls.append("artifact")
        return MemoryArtifactStore()

    def fail_build_checkpoint_store(settings: object) -> object:
        calls.append("checkpoint")
        raise RuntimeError("filesystem checkpoint store failed")

    monkeypatch.setattr(
        "langgraph_automation.apps.automation.services.runtime.build_package_artifact_store",
        build_artifact_store,
    )
    monkeypatch.setattr(
        "langgraph_automation.apps.automation.services.runtime.build_package_checkpoint_store",
        fail_build_checkpoint_store,
    )

    workflow = Workflow.objects.create(
        name='wf-persistence-checkpoint-failure',
        definition_payload=_workflow_payload(
            artifact_store={'backend': 'memory'},
            checkpoint_store={'backend': 'filesystem', 'config': {'root': str(tmp_path / 'checkpoints')}},
        ),
    )
    run = Run.objects.create(workflow=workflow, name='run-persistence-checkpoint-failure')

    with pytest.raises(RuntimeError, match='filesystem checkpoint store failed'):
        build_graph_runtime(run)

    assert calls == ['artifact', 'checkpoint']
