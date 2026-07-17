"""Runtime assembler store tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from langgraph_automation.api.errors import ArtifactPersistenceError
from langgraph_automation.api.plugins import Plugin, PluginContributions, PluginMetadata, StoreContribution
from langgraph_automation.config.models import (
    EffectivePluginSet,
    LimitsConfig,
    NormalizedPackageConfig,
    PluginsConfig,
    SafetyConfig,
    StoreBackendConfig,
    ToolsConfig,
    ValidatedPackageConfig,
)
from langgraph_automation.integrations.artifact import ArtifactReadResult, ArtifactWriteRequest, FilesystemArtifactStore, MemoryArtifactStore
from langgraph_automation.integrations.checkpoint.memory_store import MemoryCheckpointStore
from langgraph_automation.runtime import assembly as runtime_assembly
from langgraph_automation.runtime.assembly import RuntimeAssembler
from langgraph_automation.runtime.context import FactoryContext
from langgraph_automation.runtime.secrets import EnvSecretResolver


def _validated_config(
    *,
    artifact_store: StoreBackendConfig | None = None,
    checkpoint_store: StoreBackendConfig | None = None,
    checkpoint_create_store=None,
) -> ValidatedPackageConfig:
    checkpoint = StoreContribution(backend_name="memory", store_type="checkpoint", create_store=checkpoint_create_store)
    plugin = Plugin(
        metadata=PluginMetadata(name="store-plugin", version="0.1.0", plugin_types=("store",)),
        contributions=PluginContributions(stores=(checkpoint,)),
    )
    stores: dict[str, StoreBackendConfig] = {}
    if artifact_store is not None:
        stores["artifact"] = artifact_store
    if checkpoint_store is not None:
        stores["checkpoint"] = checkpoint_store
    return ValidatedPackageConfig(
        normalized=NormalizedPackageConfig(
            version=1,
            environment="test",
            plugins=PluginsConfig(enabled=("store-plugin",)),
            providers={},
            tools=ToolsConfig(),
            stores=stores,
            event_sinks={},
            limits=LimitsConfig(values={}),
            observability={},
            safety=SafetyConfig(),
            metadata={},
        ),
        effective_plugins=EffectivePluginSet(
            plugins=(plugin,),
            plugin_names=("store-plugin",),
            tools={},
            providers={},
            stores={("checkpoint", "memory"): checkpoint},
            event_sinks={},
        ),
    )


def test_default_artifact_store_is_memory_when_configuration_section_is_absent() -> None:
    validated = _validated_config()

    runtime = RuntimeAssembler(secret_resolver=EnvSecretResolver(environ={})).assemble(validated)

    assert isinstance(runtime.artifact_store, MemoryArtifactStore)
    assert runtime.checkpoint_store is None


def test_explicit_filesystem_artifact_store_is_built_from_configuration(tmp_path: Path) -> None:
    root = tmp_path / "artifacts"
    validated = _validated_config(
        artifact_store=StoreBackendConfig(backend="filesystem", config={"root": str(root)}),
        checkpoint_store=StoreBackendConfig(backend="memory"),
        checkpoint_create_store=lambda *, config, context: MemoryCheckpointStore(),
    )

    runtime_a = RuntimeAssembler(secret_resolver=EnvSecretResolver(environ={})).assemble(validated)
    assert isinstance(runtime_a.artifact_store, FilesystemArtifactStore)
    assert runtime_a.checkpoint_store is not None

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


def test_checkpoint_store_factory_still_assembles_via_plugin_hook() -> None:
    calls: list[tuple[object, object]] = []

    def create_store(*, config: object, context: FactoryContext) -> object:
        calls.append((config, context))
        return {"config": config}

    validated = _validated_config(
        checkpoint_store=StoreBackendConfig(backend="memory"),
        checkpoint_create_store=create_store,
    )

    runtime = RuntimeAssembler(secret_resolver=EnvSecretResolver(environ={})).assemble(validated)

    assert runtime.artifact_store is not None
    assert runtime.checkpoint_store == {"config": StoreBackendConfig(backend="memory")}
    assert len(calls) == 1


def test_filesystem_artifact_store_initialization_failure_propagates_without_fallback(tmp_path: Path) -> None:
    root = tmp_path / "artifacts"
    root.write_text("not a directory")
    validated = _validated_config(
        artifact_store=StoreBackendConfig(backend="filesystem", config={"root": str(root)}),
        checkpoint_store=StoreBackendConfig(backend="memory"),
    )

    with pytest.raises(ArtifactPersistenceError):
        RuntimeAssembler(secret_resolver=EnvSecretResolver(environ={})).assemble(validated)
