"""Runtime assembler store tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from langgraph_automation.config.models import (
    CheckpointStoreSettings,
    EffectivePluginSet,
    FilesystemArtifactStoreSettings,
    FilesystemCheckpointStoreSettings,
    LimitsConfig,
    MemoryCheckpointStoreSettings,
    NormalizedPackageConfig,
    PluginsConfig,
    SafetyConfig,
    StoreBackendConfig,
    ToolsConfig,
    ValidatedPackageConfig,
)
from langgraph_automation.api.errors import ArtifactPersistenceError
from langgraph_automation.integrations.artifact import ArtifactReadResult, ArtifactWriteRequest, FilesystemArtifactStore, MemoryArtifactStore
from langgraph_automation.integrations.checkpoint import CheckpointReadResult, CheckpointWriteRequest, FilesystemCheckpointStore, MemoryCheckpointStore
from langgraph_automation.runtime import assembly as runtime_assembly
from langgraph_automation.runtime.assembly import RuntimeAssembler
from langgraph_automation.runtime.secrets import EnvSecretResolver


def _validated_config(
    *,
    artifact_store: StoreBackendConfig | None = None,
    checkpoint_store: CheckpointStoreSettings | None = None,
) -> ValidatedPackageConfig:
    stores: dict[str, StoreBackendConfig] = {}
    if artifact_store is not None:
        stores["artifact"] = artifact_store
    normalized = NormalizedPackageConfig(
        version=1,
        environment="test",
        plugins=PluginsConfig(enabled=()),
        providers={},
        tools=ToolsConfig(),
        stores=stores,
        event_sinks={},
        limits=LimitsConfig(values={}),
        observability={},
        safety=SafetyConfig(),
        metadata={},
        checkpoint_store=MemoryCheckpointStoreSettings() if checkpoint_store is None else checkpoint_store,
    )
    return ValidatedPackageConfig(
        normalized=normalized,
        effective_plugins=EffectivePluginSet(
            plugins=(),
            plugin_names=(),
            tools={},
            providers={},
            stores={},
            event_sinks={},
        ),
    )


def test_default_runtime_stores_are_memory_when_configuration_sections_are_absent() -> None:
    validated = _validated_config()

    runtime = RuntimeAssembler(secret_resolver=EnvSecretResolver(environ={})).assemble(validated)

    assert isinstance(runtime.artifact_store, MemoryArtifactStore)
    assert isinstance(runtime.checkpoint_store, MemoryCheckpointStore)


def test_explicit_filesystem_artifact_store_is_built_from_configuration(tmp_path: Path) -> None:
    root = tmp_path / "artifacts"
    validated = _validated_config(
        artifact_store=StoreBackendConfig(backend="filesystem", config={"root": str(root)}),
    )

    runtime_a = RuntimeAssembler(secret_resolver=EnvSecretResolver(environ={})).assemble(validated)

    assert isinstance(runtime_a.artifact_store, FilesystemArtifactStore)
    assert isinstance(runtime_a.checkpoint_store, MemoryCheckpointStore)

    written = runtime_a.artifact_store.put(
        ArtifactWriteRequest(
            run_id=1,
            storage_key="run-1/report.md",
            body=b"hello world",
            name="report",
            kind="text",
            content_type="text/markdown",
        )
    )

    runtime_b = RuntimeAssembler(secret_resolver=EnvSecretResolver(environ={})).assemble(validated)
    fetched = runtime_b.artifact_store.get("run-1/report.md")

    assert fetched is not None
    assert isinstance(fetched, ArtifactReadResult)
    assert fetched.artifact == written
    assert fetched.body == b"hello world"


def test_explicit_filesystem_checkpoint_store_is_built_from_configuration(tmp_path: Path) -> None:
    root = tmp_path / "checkpoints"
    validated = _validated_config(
        checkpoint_store=FilesystemCheckpointStoreSettings(root=root),
    )

    runtime_a = RuntimeAssembler(secret_resolver=EnvSecretResolver(environ={})).assemble(validated)

    assert isinstance(runtime_a.artifact_store, MemoryArtifactStore)
    assert isinstance(runtime_a.checkpoint_store, FilesystemCheckpointStore)

    written = runtime_a.checkpoint_store.save(
        CheckpointWriteRequest(
            run_id=1,
            checkpoint_namespace="default",
            checkpoint_id="checkpoint-a",
            body=b"checkpoint-body",
            serializer_name="langgraph-json",
            serializer_version=1,
            content_type="application/vnd.langgraph.checkpoint+json",
        )
    )

    runtime_b = RuntimeAssembler(secret_resolver=EnvSecretResolver(environ={})).assemble(validated)
    fetched = runtime_b.checkpoint_store.load_latest(1, checkpoint_namespace="default")

    assert fetched is not None
    assert isinstance(fetched, CheckpointReadResult)
    assert fetched.checkpoint == written
    assert fetched.body == b"checkpoint-body"


def test_artifact_store_is_built_only_once_per_assembly(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[object] = []

    def fake_build_artifact_store(settings: object) -> object:
        calls.append(settings)
        return MemoryArtifactStore()

    monkeypatch.setattr(runtime_assembly, "build_artifact_store", fake_build_artifact_store)
    validated = _validated_config()

    runtime = RuntimeAssembler(secret_resolver=EnvSecretResolver(environ={})).assemble(validated)

    assert isinstance(runtime.artifact_store, MemoryArtifactStore)
    assert len(calls) == 1


def test_checkpoint_store_is_built_only_once_per_assembly(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[object] = []

    def fake_build_checkpoint_store(settings: object) -> object:
        calls.append(settings)
        return MemoryCheckpointStore()

    monkeypatch.setattr(runtime_assembly, "build_checkpoint_store", fake_build_checkpoint_store)
    validated = _validated_config(
        checkpoint_store=FilesystemCheckpointStoreSettings(root=Path("/tmp/checkpoints")),
    )

    runtime = RuntimeAssembler(secret_resolver=EnvSecretResolver(environ={})).assemble(validated)

    assert isinstance(runtime.checkpoint_store, MemoryCheckpointStore)
    assert len(calls) == 1


def test_artifact_and_checkpoint_selection_are_independent(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    artifact_root = tmp_path / "artifacts"
    checkpoint_root = tmp_path / "checkpoints"
    captured: list[tuple[str, object]] = []

    def fake_build_artifact_store(settings: object) -> object:
        captured.append(("artifact", settings))
        return MemoryArtifactStore()

    def fake_build_checkpoint_store(settings: object) -> object:
        captured.append(("checkpoint", settings))
        return MemoryCheckpointStore()

    monkeypatch.setattr(runtime_assembly, "build_artifact_store", fake_build_artifact_store)
    monkeypatch.setattr(runtime_assembly, "build_checkpoint_store", fake_build_checkpoint_store)

    validated = _validated_config(
        artifact_store=StoreBackendConfig(backend="filesystem", config={"root": str(artifact_root)}),
        checkpoint_store=FilesystemCheckpointStoreSettings(root=checkpoint_root),
    )

    runtime = RuntimeAssembler(secret_resolver=EnvSecretResolver(environ={})).assemble(validated)

    assert isinstance(runtime.artifact_store, MemoryArtifactStore)
    assert isinstance(runtime.checkpoint_store, MemoryCheckpointStore)
    assert captured[0][0] == "artifact"
    assert captured[1][0] == "checkpoint"
    assert captured[0][1] == FilesystemArtifactStoreSettings(root=artifact_root)
    assert captured[1][1] == FilesystemCheckpointStoreSettings(root=checkpoint_root)


def test_filesystem_artifact_store_initialization_failure_propagates_without_fallback(tmp_path: Path) -> None:
    root = tmp_path / "artifacts"
    root.write_text("not a directory")
    validated = _validated_config(
        artifact_store=StoreBackendConfig(backend="filesystem", config={"root": str(root)}),
    )

    with pytest.raises(ArtifactPersistenceError):
        RuntimeAssembler(secret_resolver=EnvSecretResolver(environ={})).assemble(validated)
