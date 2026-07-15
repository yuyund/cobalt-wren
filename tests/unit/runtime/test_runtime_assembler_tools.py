"""Runtime assembler tool tests."""

from __future__ import annotations

import pytest

from langgraph_automation.api.errors import RuntimeAssemblyError
from langgraph_automation.api.plugins import Plugin, PluginContributions, PluginMetadata, ToolContribution
from langgraph_automation.config.models import (
    EffectivePluginSet,
    LimitsConfig,
    NormalizedPackageConfig,
    PluginsConfig,
    SafetyConfig,
    ToolsConfig,
    ValidatedPackageConfig,
)
from langgraph_automation.runtime.assembly import RuntimeAssembler
from langgraph_automation.runtime.context import FactoryContext
from langgraph_automation.runtime.secrets import EnvSecretResolver


def _validated_config(*, create_tool, validate_config=None, configs: dict[str, object] | None = None) -> tuple[ValidatedPackageConfig, list[tuple[object, object]]]:
    calls: list[tuple[object, object]] = []

    def _create_tool(*, config: object, context: FactoryContext):
        calls.append((config, context))
        return create_tool(config=config, context=context)

    tool = ToolContribution(
        name="github.search_issues",
        validate_config=validate_config,
        create_tool=_create_tool,
    )
    plugin = Plugin(
        metadata=PluginMetadata(name="tool-plugin", version="0.1.0", plugin_types=("tool",)),
        contributions=PluginContributions(tools=(tool,)),
    )
    normalized = NormalizedPackageConfig(
        version=1,
        environment="test",
        plugins=PluginsConfig(enabled=("tool-plugin",)),
        providers={},
        tools=ToolsConfig(allowlist=("github.search_issues",), configs=configs or {}),
        stores={},
        event_sinks={},
        limits=LimitsConfig(values={}),
        observability={},
        safety=SafetyConfig(),
        metadata={},
    )
    validated = ValidatedPackageConfig(
        normalized=normalized,
        effective_plugins=EffectivePluginSet(plugins=(plugin,), plugin_names=("tool-plugin",), tools={"github.search_issues": tool}, providers={}, stores={}, event_sinks={}),
    )
    return validated, calls


def test_allowlisted_tool_factory_called_with_keyword_config_and_context() -> None:
    observed: list[tuple[object, FactoryContext]] = []

    def create_tool(*, config: object, context: FactoryContext) -> object:
        observed.append((config, context))
        return {"tool": config}

    validated, _ = _validated_config(create_tool=create_tool, configs={"github.search_issues": {"timeout_seconds": 10}})

    dependencies = RuntimeAssembler(secret_resolver=EnvSecretResolver(environ={})).assemble(validated)

    assert dependencies.tools["github.search_issues"] == {"tool": {"timeout_seconds": 10}}
    assert len(observed) == 1
    assert observed[0][0] == {"timeout_seconds": 10}


def test_missing_tool_config_passes_empty_mapping() -> None:
    observed: list[object] = []

    def create_tool(*, config: object, context: FactoryContext) -> object:
        observed.append(config)
        return object()

    validated, _ = _validated_config(create_tool=create_tool)

    RuntimeAssembler(secret_resolver=EnvSecretResolver(environ={})).assemble(validated)

    assert observed == [{}]


def test_missing_tool_factory_raises_runtime_assembly_error() -> None:
    tool = ToolContribution(name="github.search_issues", create_tool=None)
    plugin = Plugin(metadata=PluginMetadata(name="tool-plugin", version="0.1.0", plugin_types=("tool",)), contributions=PluginContributions(tools=(tool,)))
    validated = ValidatedPackageConfig(
        normalized=NormalizedPackageConfig(
            version=1,
            environment="test",
            plugins=PluginsConfig(enabled=("tool-plugin",)),
            providers={},
            tools=ToolsConfig(allowlist=("github.search_issues",)),
            stores={},
            event_sinks={},
            limits=LimitsConfig(values={}),
            observability={},
            safety=SafetyConfig(),
            metadata={},
        ),
        effective_plugins=EffectivePluginSet(plugins=(plugin,), plugin_names=("tool-plugin",), tools={"github.search_issues": tool}, providers={}, stores={}, event_sinks={}),
    )

    with pytest.raises(RuntimeAssemblyError) as excinfo:
        RuntimeAssembler(secret_resolver=EnvSecretResolver(environ={})).assemble(validated)

    assert excinfo.value.code == "RUNTIME_ASSEMBLY_FACTORY_MISSING"


def test_tool_factory_arbitrary_exception_is_wrapped() -> None:
    def create_tool(*, config: object, context: FactoryContext) -> object:
        raise ValueError("boom")

    validated, _ = _validated_config(create_tool=create_tool)

    with pytest.raises(RuntimeAssemblyError) as excinfo:
        RuntimeAssembler(secret_resolver=EnvSecretResolver(environ={})).assemble(validated)

    assert excinfo.value.code == "RUNTIME_ASSEMBLY_TOOL_FAILED"
    assert isinstance(excinfo.value.__cause__, ValueError)


def test_tool_factory_returning_none_raises_runtime_assembly_error() -> None:
    def create_tool(*, config: object, context: FactoryContext) -> object | None:
        return None

    validated, _ = _validated_config(create_tool=create_tool)

    with pytest.raises(RuntimeAssemblyError) as excinfo:
        RuntimeAssembler(secret_resolver=EnvSecretResolver(environ={})).assemble(validated)

    assert excinfo.value.code == "RUNTIME_ASSEMBLY_INVALID_FACTORY_RESULT"


def test_tool_validation_hook_is_not_called_during_assembly() -> None:
    def validate_config(*, config: object, context: FactoryContext) -> None:
        raise AssertionError("validate_config should not be called")

    validated, _ = _validated_config(create_tool=lambda *, config, context: object(), validate_config=validate_config)

    RuntimeAssembler(secret_resolver=EnvSecretResolver(environ={})).assemble(validated)
