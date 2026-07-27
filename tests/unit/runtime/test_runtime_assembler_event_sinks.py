"""Runtime assembler event sink tests."""

from __future__ import annotations

import pytest

from cobalt_wren.api.errors import RuntimeAssemblyError
from cobalt_wren.api.plugins import EventSinkContribution, Plugin, PluginContributions, PluginMetadata
from cobalt_wren.config.models import (
    EffectivePluginSet,
    EventSinkBackendConfig,
    LimitsConfig,
    NormalizedPackageConfig,
    PluginsConfig,
    ToolsConfig,
    SafetyConfig,
    ValidatedPackageConfig,
)
from cobalt_wren.runtime.assembly import RuntimeAssembler
from cobalt_wren.runtime.context import FactoryContext
from cobalt_wren.runtime.secrets import EnvSecretResolver


def _validated_config(*, create_sink, validate_config=None) -> tuple[ValidatedPackageConfig, list[tuple[object, object]]]:
    calls: list[tuple[object, object]] = []

    def _create_sink(*, config: object, context: FactoryContext):
        calls.append((config, context))
        return create_sink(config=config, context=context)

    sink = EventSinkContribution(backend_name="stdout", validate_config=validate_config, create_sink=_create_sink)
    plugin = Plugin(
        metadata=PluginMetadata(name="sink-plugin", version="0.1.0", plugin_types=("event_sink",)),
        contributions=PluginContributions(event_sinks=(sink,)),
    )
    validated = ValidatedPackageConfig(
        normalized=NormalizedPackageConfig(
            version=1,
            environment="test",
            plugins=PluginsConfig(enabled=("sink-plugin",)),
            providers={},
            tools=ToolsConfig(),
            stores={},
            event_sinks={"stdout": EventSinkBackendConfig(backend="stdout", config={"format": "json"})},
            limits=LimitsConfig(values={}),
            observability={},
            safety=SafetyConfig(),
            metadata={},
        ),
        effective_plugins=EffectivePluginSet(plugins=(plugin,), plugin_names=("sink-plugin",), tools={}, providers={}, stores={}, event_sinks={"stdout": sink}),
    )
    return validated, calls


def test_event_sink_factory_called_with_keyword_config_and_context() -> None:
    observed: list[tuple[object, FactoryContext]] = []

    def create_sink(*, config: object, context: FactoryContext) -> object:
        observed.append((config, context))
        return {"sink": config}

    validated, _ = _validated_config(create_sink=create_sink)

    dependencies = RuntimeAssembler(secret_resolver=EnvSecretResolver(environ={})).assemble(validated)

    assert dependencies.event_sinks["stdout"] == {"sink": EventSinkBackendConfig(backend="stdout", config={"format": "json"})}
    assert len(observed) == 1
    assert isinstance(observed[0][1], FactoryContext)


def test_missing_event_sink_factory_raises_runtime_assembly_error() -> None:
    sink = EventSinkContribution(backend_name="stdout", create_sink=None)
    plugin = Plugin(metadata=PluginMetadata(name="sink-plugin", version="0.1.0", plugin_types=("event_sink",)), contributions=PluginContributions(event_sinks=(sink,)))
    validated = ValidatedPackageConfig(
        normalized=NormalizedPackageConfig(
            version=1,
            environment="test",
            plugins=PluginsConfig(enabled=("sink-plugin",)),
            providers={},
            tools=ToolsConfig(),
            stores={},
            event_sinks={"stdout": EventSinkBackendConfig(backend="stdout")},
            limits=LimitsConfig(values={}),
            observability={},
            safety=SafetyConfig(),
            metadata={},
        ),
        effective_plugins=EffectivePluginSet(plugins=(plugin,), plugin_names=("sink-plugin",), tools={}, providers={}, stores={}, event_sinks={"stdout": sink}),
    )

    with pytest.raises(RuntimeAssemblyError) as excinfo:
        RuntimeAssembler(secret_resolver=EnvSecretResolver(environ={})).assemble(validated)

    assert excinfo.value.code == "RUNTIME_ASSEMBLY_FACTORY_MISSING"


def test_event_sink_factory_arbitrary_exception_is_wrapped() -> None:
    def create_sink(*, config: object, context: FactoryContext) -> object:
        raise ValueError("boom")

    validated, _ = _validated_config(create_sink=create_sink)

    with pytest.raises(RuntimeAssemblyError) as excinfo:
        RuntimeAssembler(secret_resolver=EnvSecretResolver(environ={})).assemble(validated)

    assert excinfo.value.code == "RUNTIME_ASSEMBLY_EVENT_SINK_FAILED"
    assert isinstance(excinfo.value.__cause__, ValueError)


def test_event_sink_factory_returning_none_raises_runtime_assembly_error() -> None:
    def create_sink(*, config: object, context: FactoryContext) -> object | None:
        return None

    validated, _ = _validated_config(create_sink=create_sink)

    with pytest.raises(RuntimeAssemblyError) as excinfo:
        RuntimeAssembler(secret_resolver=EnvSecretResolver(environ={})).assemble(validated)

    assert excinfo.value.code == "RUNTIME_ASSEMBLY_INVALID_FACTORY_RESULT"


def test_event_sink_validation_hook_is_not_called_during_assembly() -> None:
    def validate_config(*, config: object, context: FactoryContext) -> None:
        raise AssertionError("validate_config should not be called")

    validated, _ = _validated_config(create_sink=lambda *, config, context: object(), validate_config=validate_config)

    RuntimeAssembler(secret_resolver=EnvSecretResolver(environ={})).assemble(validated)
