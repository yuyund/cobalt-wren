"""Runtime assembler store tests."""

from __future__ import annotations

import pytest

from langgraph_automation.api.errors import RuntimeAssemblyError
from langgraph_automation.api.plugins import Plugin, PluginContributions, PluginMetadata, StoreContribution
from langgraph_automation.config.models import (
    EffectivePluginSet,
    LimitsConfig,
    NormalizedPackageConfig,
    PluginsConfig,
    ToolsConfig,
    SafetyConfig,
    StoreBackendConfig,
    ValidatedPackageConfig,
)
from langgraph_automation.runtime.assembly import RuntimeAssembler
from langgraph_automation.runtime.context import FactoryContext
from langgraph_automation.runtime.secrets import EnvSecretResolver


def _validated_config(*, create_store_artifact=None, create_store_checkpoint=None, store_type: str = "artifact") -> ValidatedPackageConfig:
    artifact = StoreContribution(backend_name="memory", store_type="artifact", create_store=create_store_artifact)
    checkpoint = StoreContribution(backend_name="memory", store_type="checkpoint", create_store=create_store_checkpoint)
    plugin = Plugin(
        metadata=PluginMetadata(name="store-plugin", version="0.1.0", plugin_types=("store",)),
        contributions=PluginContributions(stores=(artifact, checkpoint)),
    )
    return ValidatedPackageConfig(
        normalized=NormalizedPackageConfig(
            version=1,
            environment="test",
            plugins=PluginsConfig(enabled=("store-plugin",)),
            providers={},
            tools=ToolsConfig(),
            stores={
                store_type: StoreBackendConfig(backend="memory"),
            },
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
            stores={("artifact", "memory"): artifact, ("checkpoint", "memory"): checkpoint},
            event_sinks={},
        ),
    )


def test_artifact_and_checkpoint_stores_are_assembled() -> None:
    calls: list[tuple[object, object]] = []

    def create_store(*, config: object, context: FactoryContext) -> object:
        calls.append((config, context))
        if isinstance(config, StoreBackendConfig) and config.backend == "memory":
            return {"store_type": config}
        return {"store": config}

    validated = _validated_config(create_store_artifact=create_store, create_store_checkpoint=create_store, store_type="artifact")
    validated = ValidatedPackageConfig(
        normalized=NormalizedPackageConfig(
            version=1,
            environment="test",
            plugins=PluginsConfig(enabled=("store-plugin",)),
            providers={},
            tools=ToolsConfig(),
            stores={
                "artifact": StoreBackendConfig(backend="memory", config={"root": "var/artifacts"}),
                "checkpoint": StoreBackendConfig(backend="memory", config={"path": "var/checkpoints.sqlite"}),
            },
            event_sinks={},
            limits=LimitsConfig(values={}),
            observability={},
            safety=SafetyConfig(),
            metadata={},
        ),
        effective_plugins=validated.effective_plugins,
    )

    dependencies = RuntimeAssembler(secret_resolver=EnvSecretResolver(environ={})).assemble(validated)

    assert dependencies.artifact_store is not None
    assert dependencies.checkpoint_store is not None
    assert len(calls) == 2


def test_same_backend_name_different_store_types_work() -> None:
    def create_store(*, config: object, context: FactoryContext) -> object:
        return {"config": config}

    validated = _validated_config(create_store_artifact=create_store, create_store_checkpoint=create_store, store_type="artifact")
    validated = ValidatedPackageConfig(
        normalized=NormalizedPackageConfig(
            version=1,
            environment="test",
            plugins=PluginsConfig(enabled=("store-plugin",)),
            providers={},
            tools=ToolsConfig(),
            stores={
                "artifact": StoreBackendConfig(backend="memory"),
                "checkpoint": StoreBackendConfig(backend="memory"),
            },
            event_sinks={},
            limits=LimitsConfig(values={}),
            observability={},
            safety=SafetyConfig(),
            metadata={},
        ),
        effective_plugins=validated.effective_plugins,
    )

    dependencies = RuntimeAssembler(secret_resolver=EnvSecretResolver(environ={})).assemble(validated)

    assert dependencies.artifact_store == {"config": StoreBackendConfig(backend="memory")}
    assert dependencies.checkpoint_store == {"config": StoreBackendConfig(backend="memory")}


def test_missing_store_factory_raises_runtime_assembly_error() -> None:
    validated = _validated_config(create_store_artifact=None, create_store_checkpoint=None, store_type="artifact")

    with pytest.raises(RuntimeAssemblyError) as excinfo:
        RuntimeAssembler(secret_resolver=EnvSecretResolver(environ={})).assemble(validated)

    assert excinfo.value.code == "RUNTIME_ASSEMBLY_FACTORY_MISSING"


def test_unsupported_store_type_raises_runtime_assembly_error() -> None:
    artifact = StoreContribution(backend_name="memory", store_type="artifact", create_store=lambda *, config, context: object())
    plugin = Plugin(metadata=PluginMetadata(name="store-plugin", version="0.1.0", plugin_types=("store",)), contributions=PluginContributions(stores=(artifact,)))
    validated = ValidatedPackageConfig(
        normalized=NormalizedPackageConfig(
            version=1,
            environment="test",
            plugins=PluginsConfig(enabled=("store-plugin",)),
            providers={},
            tools=ToolsConfig(),
            stores={"vector": StoreBackendConfig(backend="memory")},
            event_sinks={},
            limits=LimitsConfig(values={}),
            observability={},
            safety=SafetyConfig(),
            metadata={},
        ),
        effective_plugins=EffectivePluginSet(plugins=(plugin,), plugin_names=("store-plugin",), tools={}, providers={}, stores={("vector", "memory"): artifact}, event_sinks={}),
    )

    with pytest.raises(RuntimeAssemblyError) as excinfo:
        RuntimeAssembler(secret_resolver=EnvSecretResolver(environ={})).assemble(validated)

    assert excinfo.value.code == "RUNTIME_ASSEMBLY_UNSUPPORTED_STORE_TYPE"


def test_store_factory_arbitrary_exception_is_wrapped() -> None:
    def create_store(*, config: object, context: FactoryContext) -> object:
        raise ValueError("boom")

    validated = _validated_config(create_store_artifact=create_store, create_store_checkpoint=create_store, store_type="artifact")

    with pytest.raises(RuntimeAssemblyError) as excinfo:
        RuntimeAssembler(secret_resolver=EnvSecretResolver(environ={})).assemble(validated)

    assert excinfo.value.code == "RUNTIME_ASSEMBLY_STORE_FAILED"
    assert isinstance(excinfo.value.__cause__, ValueError)


def test_store_factory_returning_none_raises_runtime_assembly_error() -> None:
    def create_store(*, config: object, context: FactoryContext) -> object | None:
        return None

    validated = _validated_config(create_store_artifact=create_store, create_store_checkpoint=create_store, store_type="artifact")

    with pytest.raises(RuntimeAssemblyError) as excinfo:
        RuntimeAssembler(secret_resolver=EnvSecretResolver(environ={})).assemble(validated)

    assert excinfo.value.code == "RUNTIME_ASSEMBLY_INVALID_FACTORY_RESULT"


def test_store_validation_hook_is_not_called_during_assembly() -> None:
    artifact = StoreContribution(backend_name="memory", store_type="artifact", validate_config=lambda **kwargs: (_ for _ in ()).throw(AssertionError("validate_config should not be called")), create_store=lambda *, config, context: object())
    plugin = Plugin(metadata=PluginMetadata(name="store-plugin", version="0.1.0", plugin_types=("store",)), contributions=PluginContributions(stores=(artifact,)))
    validated = ValidatedPackageConfig(
        normalized=NormalizedPackageConfig(
            version=1,
            environment="test",
            plugins=PluginsConfig(enabled=("store-plugin",)),
            providers={},
            tools=ToolsConfig(),
            stores={"artifact": StoreBackendConfig(backend="memory")},
            event_sinks={},
            limits=LimitsConfig(values={}),
            observability={},
            safety=SafetyConfig(),
            metadata={},
        ),
        effective_plugins=EffectivePluginSet(plugins=(plugin,), plugin_names=("store-plugin",), tools={}, providers={}, stores={("artifact", "memory"): artifact}, event_sinks={}),
    )

    RuntimeAssembler(secret_resolver=EnvSecretResolver(environ={})).assemble(validated)
