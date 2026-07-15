"""Runtime assembler provider tests."""

from __future__ import annotations

import pytest

from langgraph_automation.api.errors import RuntimeAssemblyError
from langgraph_automation.api.plugins import Plugin, PluginContributions, PluginMetadata, ProviderContribution
from langgraph_automation.config.models import (
    EffectivePluginSet,
    LimitsConfig,
    NormalizedPackageConfig,
    PluginsConfig,
    ProviderProfileConfig,
    ToolsConfig,
    SafetyConfig,
    ValidatedPackageConfig,
    SecretRef,
)
from langgraph_automation.runtime.assembly import RuntimeAssembler
from langgraph_automation.runtime.context import FactoryContext
from langgraph_automation.runtime.secrets import EnvSecretResolver


def _validated_config(*, create_client, validate_profile=None) -> tuple[ValidatedPackageConfig, list[tuple[object, object]]]:
    calls: list[tuple[object, object]] = []

    def _create_client(*, config: ProviderProfileConfig, context: FactoryContext):
        calls.append((config, context))
        return create_client(config=config, context=context)

    provider = ProviderContribution(
        name="litellm",
        provider_type="llm",
        validate_profile=validate_profile,
        create_client=_create_client,
    )
    plugin = Plugin(
        metadata=PluginMetadata(name="provider-plugin", version="0.1.0", plugin_types=("provider",)),
        contributions=PluginContributions(providers=(provider,)),
    )
    normalized = NormalizedPackageConfig(
        version=1,
        environment="test",
        plugins=PluginsConfig(enabled=("provider-plugin",)),
        providers={
            "default": ProviderProfileConfig(
                provider="litellm",
                model="gpt-4.1-mini",
                secrets={"api_key": SecretRef(source="env", name="OPENAI_API_KEY")},
            ),
        },
        tools=ToolsConfig(),
        stores={},
        event_sinks={},
        limits=LimitsConfig(values={"max_steps": 3}),
        observability={"capture": {"input_summary": True}},
        safety=SafetyConfig(),
        metadata={},
    )
    validated = ValidatedPackageConfig(
        normalized=normalized,
        effective_plugins=EffectivePluginSet(
            plugins=(plugin,),
            plugin_names=("provider-plugin",),
            tools={},
            providers={"litellm": provider},
            stores={},
            event_sinks={},
        ),
    )
    return validated, calls


def test_provider_factory_called_with_keyword_config_and_context() -> None:
    observed: list[tuple[ProviderProfileConfig, FactoryContext]] = []

    def create_client(*, config: ProviderProfileConfig, context: FactoryContext) -> object:
        observed.append((config, context))
        return {"client": context.secrets.resolve(config.secrets["api_key"])}

    validated, _ = _validated_config(create_client=create_client)
    assembler = RuntimeAssembler(secret_resolver=EnvSecretResolver(environ={"OPENAI_API_KEY": "test-key"}))

    dependencies = assembler.assemble(validated)

    assert dependencies.providers["default"] == {"client": "test-key"}
    assert len(observed) == 1
    assert observed[0][0] == validated.normalized.providers["default"]
    assert isinstance(observed[0][1], FactoryContext)


def test_missing_provider_factory_raises_runtime_assembly_error() -> None:
    provider = ProviderContribution(name="litellm", provider_type="llm", create_client=None)
    plugin = Plugin(
        metadata=PluginMetadata(name="provider-plugin", version="0.1.0", plugin_types=("provider",)),
        contributions=PluginContributions(providers=(provider,)),
    )
    validated = ValidatedPackageConfig(
        normalized=NormalizedPackageConfig(
            version=1,
            environment="test",
            plugins=PluginsConfig(enabled=("provider-plugin",)),
            providers={"default": ProviderProfileConfig(provider="litellm", model="gpt-4.1-mini")},
            tools={},
            stores={},
            event_sinks={},
            limits=LimitsConfig(values={}),
            observability={},
            safety=SafetyConfig(),
            metadata={},
        ),
        effective_plugins=EffectivePluginSet(plugins=(plugin,), plugin_names=("provider-plugin",), tools={}, providers={"litellm": provider}, stores={}, event_sinks={}),
    )

    with pytest.raises(RuntimeAssemblyError) as excinfo:
        RuntimeAssembler().assemble(validated)

    assert excinfo.value.code == "RUNTIME_ASSEMBLY_FACTORY_MISSING"
    assert excinfo.value.component == "runtime_assembly"


def test_provider_factory_arbitrary_exception_is_wrapped() -> None:
    def create_client(*, config: ProviderProfileConfig, context: FactoryContext) -> object:
        raise ValueError("boom")

    validated, _ = _validated_config(create_client=create_client)

    with pytest.raises(RuntimeAssemblyError) as excinfo:
        RuntimeAssembler(secret_resolver=EnvSecretResolver(environ={"OPENAI_API_KEY": "test-key"})).assemble(validated)

    assert excinfo.value.code == "RUNTIME_ASSEMBLY_PROVIDER_FAILED"
    assert isinstance(excinfo.value.__cause__, ValueError)


def test_provider_factory_runtime_assembly_error_is_preserved() -> None:
    error = RuntimeAssemblyError("provider already failed", code="RUNTIME_ASSEMBLY_PROVIDER_FAILED", component="plugin")

    def create_client(*, config: ProviderProfileConfig, context: FactoryContext) -> object:
        raise error

    validated, _ = _validated_config(create_client=create_client)

    with pytest.raises(RuntimeAssemblyError) as excinfo:
        RuntimeAssembler(secret_resolver=EnvSecretResolver(environ={"OPENAI_API_KEY": "test-key"})).assemble(validated)

    assert excinfo.value is error


def test_provider_factory_returning_none_raises_runtime_assembly_error() -> None:
    def create_client(*, config: ProviderProfileConfig, context: FactoryContext) -> object | None:
        return None

    validated, _ = _validated_config(create_client=create_client)

    with pytest.raises(RuntimeAssemblyError) as excinfo:
        RuntimeAssembler(secret_resolver=EnvSecretResolver(environ={"OPENAI_API_KEY": "test-key"})).assemble(validated)

    assert excinfo.value.code == "RUNTIME_ASSEMBLY_INVALID_FACTORY_RESULT"


def test_provider_factory_can_resolve_secret_through_context() -> None:
    def create_client(*, config: ProviderProfileConfig, context: FactoryContext) -> object:
        return {"api_key": context.secrets.resolve(config.secrets["api_key"])}

    validated, _ = _validated_config(create_client=create_client)

    dependencies = RuntimeAssembler(secret_resolver=EnvSecretResolver(environ={"OPENAI_API_KEY": "test-key"})).assemble(validated)

    assert dependencies.providers["default"] == {"api_key": "test-key"}


def test_provider_validation_hook_is_not_called_during_assembly() -> None:
    def validate_profile(*, config: ProviderProfileConfig, context: FactoryContext) -> None:
        raise AssertionError("validate_profile should not be called")

    validated, _ = _validated_config(create_client=lambda *, config, context: object(), validate_profile=validate_profile)

    RuntimeAssembler(secret_resolver=EnvSecretResolver(environ={"OPENAI_API_KEY": "test-key"})).assemble(validated)
