"""PluginRegistry tests."""

from __future__ import annotations

import pytest

from cobalt_wren.api.errors import PluginRegistrationError, PluginResolutionError
from cobalt_wren.api.plugins import (
    EventSinkContribution,
    Plugin,
    PluginContributions,
    PluginMetadata,
    ProviderContribution,
    StoreContribution,
    ToolContribution,
)
from cobalt_wren.plugins.registry import PluginRegistry


def _build_plugin(
    name: str,
    *,
    tool_name: str | None = None,
    provider_name: str | None = None,
    artifact_store_backend: str | None = None,
    checkpoint_store_backend: str | None = None,
    event_sink_backend: str | None = None,
    validate_marker: list[str] | None = None,
    create_marker: list[str] | None = None,
) -> Plugin:
    def _validate(*args, **kwargs):
        if validate_marker is not None:
            validate_marker.append(name)
        raise AssertionError('validate_config should not be called during registration')

    def _create(*args, **kwargs):
        if create_marker is not None:
            create_marker.append(name)
        raise AssertionError('factory hook should not be called during registration')

    tools = () if tool_name is None else (ToolContribution(name=tool_name, validate_config=_validate, create_tool=_create),)
    providers = () if provider_name is None else (ProviderContribution(name=provider_name, provider_type='llm', validate_profile=_validate, create_client=_create),)
    stores: tuple[StoreContribution, ...] = ()
    if artifact_store_backend is not None:
        stores += (StoreContribution(backend_name=artifact_store_backend, store_type='artifact', validate_config=_validate, create_store=_create),)
    if checkpoint_store_backend is not None:
        stores += (StoreContribution(backend_name=checkpoint_store_backend, store_type='checkpoint', validate_config=_validate, create_store=_create),)
    event_sinks = () if event_sink_backend is None else (EventSinkContribution(backend_name=event_sink_backend, validate_config=_validate, create_sink=_create),)

    return Plugin(
        metadata=PluginMetadata(name=name, version='0.1.0', plugin_types=('tool', 'provider', 'store', 'event_sink')),
        contributions=PluginContributions(
            tools=tools,
            providers=providers,
            stores=stores,
            event_sinks=event_sinks,
        ),
    )


def test_registry_registers_and_looks_up_contributions() -> None:
    registry = PluginRegistry()
    plugin = _build_plugin(
        'github',
        tool_name='github.search_issues',
        provider_name='litellm',
        artifact_store_backend='memory',
        event_sink_backend='stdout',
    )

    registry.register(plugin)

    assert registry.list_plugins() == (plugin,)
    assert registry.get_plugin('github') is plugin
    assert registry.get_tool('github.search_issues') is plugin.contributions.tools[0]
    assert registry.get_provider('litellm') is plugin.contributions.providers[0]
    assert registry.get_store('artifact', 'memory') is plugin.contributions.stores[0]
    assert registry.get_event_sink('stdout') is plugin.contributions.event_sinks[0]


def test_registry_rejects_duplicate_plugin_name() -> None:
    registry = PluginRegistry()
    registry.register(_build_plugin('github', tool_name='github.search_issues'))

    with pytest.raises(PluginRegistrationError) as excinfo:
        registry.register(_build_plugin('github', tool_name='github.create_issue'))

    assert excinfo.value.code == 'PLUGIN_DUPLICATE_NAME'
    assert excinfo.value.category == 'plugin_registration'
    assert excinfo.value.component == 'plugin_registry'
    assert excinfo.value.metadata['plugin_name'] == 'github'


def test_registry_rejects_duplicate_tool_name() -> None:
    registry = PluginRegistry()
    registry.register(_build_plugin('github', tool_name='github.search_issues'))

    with pytest.raises(PluginRegistrationError) as excinfo:
        registry.register(_build_plugin('slack', tool_name='github.search_issues'))

    assert excinfo.value.code == 'PLUGIN_CONTRIBUTION_CONFLICT'
    assert excinfo.value.metadata['contribution_scope'] == 'tools'
    assert excinfo.value.metadata['contribution_name'] == 'github.search_issues'


def test_registry_rejects_duplicate_provider_name() -> None:
    registry = PluginRegistry()
    registry.register(_build_plugin('github', provider_name='litellm'))

    with pytest.raises(PluginRegistrationError) as excinfo:
        registry.register(_build_plugin('slack', provider_name='litellm'))

    assert excinfo.value.code == 'PLUGIN_CONTRIBUTION_CONFLICT'
    assert excinfo.value.metadata['contribution_scope'] == 'providers'
    assert excinfo.value.metadata['contribution_name'] == 'litellm'


def test_registry_rejects_duplicate_store_backend_with_same_store_type() -> None:
    registry = PluginRegistry()
    registry.register(_build_plugin('github', artifact_store_backend='memory'))

    with pytest.raises(PluginRegistrationError) as excinfo:
        registry.register(_build_plugin('slack', artifact_store_backend='memory'))

    assert excinfo.value.code == 'PLUGIN_CONTRIBUTION_CONFLICT'
    assert excinfo.value.metadata['store_type'] == 'artifact'
    assert excinfo.value.metadata['backend_name'] == 'memory'


def test_registry_allows_same_backend_name_for_different_store_types() -> None:
    registry = PluginRegistry()
    artifact_plugin = _build_plugin('artifact-plugin', artifact_store_backend='memory')
    checkpoint_plugin = _build_plugin('checkpoint-plugin', checkpoint_store_backend='memory')

    registry.register(artifact_plugin)
    registry.register(checkpoint_plugin)

    assert registry.get_store('artifact', 'memory') is artifact_plugin.contributions.stores[0]
    assert registry.get_store('checkpoint', 'memory') is checkpoint_plugin.contributions.stores[0]


def test_registry_rejects_duplicate_event_sink_backend() -> None:
    registry = PluginRegistry()
    registry.register(_build_plugin('github', event_sink_backend='stdout'))

    with pytest.raises(PluginRegistrationError) as excinfo:
        registry.register(_build_plugin('slack', event_sink_backend='stdout'))

    assert excinfo.value.code == 'PLUGIN_CONTRIBUTION_CONFLICT'
    assert excinfo.value.metadata['contribution_scope'] == 'event_sinks'
    assert excinfo.value.metadata['contribution_name'] == 'stdout'


def test_registry_raises_resolution_error_for_unknown_lookups() -> None:
    registry = PluginRegistry()

    with pytest.raises(PluginResolutionError) as plugin_exc:
        registry.get_plugin('missing')
    assert plugin_exc.value.code == 'PLUGIN_UNKNOWN'

    with pytest.raises(PluginResolutionError) as tool_exc:
        registry.get_tool('missing.tool')
    assert tool_exc.value.code == 'PLUGIN_UNKNOWN_TOOL'

    with pytest.raises(PluginResolutionError) as provider_exc:
        registry.get_provider('missing-provider')
    assert provider_exc.value.code == 'PLUGIN_UNKNOWN_PROVIDER'

    with pytest.raises(PluginResolutionError) as store_exc:
        registry.get_store('artifact', 'missing')
    assert store_exc.value.code == 'PLUGIN_UNKNOWN_STORE'

    with pytest.raises(PluginResolutionError) as sink_exc:
        registry.get_event_sink('missing')
    assert sink_exc.value.code == 'PLUGIN_UNKNOWN_EVENT_SINK'


def test_registry_does_not_call_validation_or_factory_hooks_during_registration() -> None:
    validate_calls: list[str] = []
    create_calls: list[str] = []
    registry = PluginRegistry()
    plugin = _build_plugin(
        'github',
        tool_name='github.search_issues',
        provider_name='litellm',
        artifact_store_backend='memory',
        event_sink_backend='stdout',
        validate_marker=validate_calls,
        create_marker=create_calls,
    )

    registry.register(plugin)

    assert validate_calls == []
    assert create_calls == []
