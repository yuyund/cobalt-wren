"""Public plugin contribution behavior tests."""

from __future__ import annotations

from langgraph_automation.api.plugins import (
    EventSinkContribution,
    Plugin,
    PluginContributions,
    PluginMetadata,
    ProviderContribution,
    StoreContribution,
    ToolContribution,
)


def test_plugin_metadata_normalizes_and_copies_mappings() -> None:
    provides = {'tools': ['github.search_issues', 'github.create_issue'], 'providers': ('litellm',)}
    requires = {'public_api_version': '>=0.1,<1.0'}
    metadata = {'team': 'platform'}

    plugin_metadata = PluginMetadata(
        name='github',
        version='0.1.0',
        description='GitHub integration plugin',
        plugin_types=['tool', 'ui'],
        provides=provides,
        requires=requires,
        metadata=metadata,
    )

    assert plugin_metadata.name == 'github'
    assert plugin_metadata.version == '0.1.0'
    assert plugin_metadata.description == 'GitHub integration plugin'
    assert plugin_metadata.plugin_types == ('tool', 'ui')
    assert plugin_metadata.provides['tools'] == ('github.search_issues', 'github.create_issue')
    assert plugin_metadata.provides['providers'] == ('litellm',)
    assert plugin_metadata.requires == requires
    assert plugin_metadata.metadata == metadata
    assert plugin_metadata.metadata is not metadata
    assert plugin_metadata.provides is not provides


def test_plugin_contributions_defaults_to_empty_tuples() -> None:
    contributions = PluginContributions()

    assert contributions.tools == ()
    assert contributions.providers == ()
    assert contributions.stores == ()
    assert contributions.event_sinks == ()


def test_plugin_contributions_normalize_iterables_to_tuples() -> None:
    tool = ToolContribution(name='github.search_issues')
    provider = ProviderContribution(name='litellm', provider_type='llm')
    store = StoreContribution(backend_name='memory', store_type='artifact')
    sink = EventSinkContribution(backend_name='stdout')

    contributions = PluginContributions(
        tools=[tool],
        providers=[provider],
        stores=[store],
        event_sinks=[sink],
    )

    assert contributions.tools == (tool,)
    assert contributions.providers == (provider,)
    assert contributions.stores == (store,)
    assert contributions.event_sinks == (sink,)


def test_plugin_holds_metadata_and_contributions() -> None:
    metadata = PluginMetadata(name='github', version='0.1.0')
    contributions = PluginContributions(tools=(ToolContribution(name='github.search_issues'),))

    plugin = Plugin(metadata=metadata, contributions=contributions)

    assert plugin.metadata is metadata
    assert plugin.contributions is contributions


def test_tool_contribution_normalizes_and_copies_fields() -> None:
    input_schema = {'type': 'object'}
    output_schema = {'type': 'string'}
    safety_metadata = {'capture': 'bounded'}
    metadata = {'source': 'github'}

    contribution = ToolContribution(
        name='github.search_issues',
        description='Search GitHub issues',
        capabilities=['search', 'read'],
        input_schema=input_schema,
        output_schema=output_schema,
        safety_metadata=safety_metadata,
        validate_config=lambda *args, **kwargs: None,
        create_tool=lambda *args, **kwargs: object(),
        metadata=metadata,
    )

    assert contribution.name == 'github.search_issues'
    assert contribution.description == 'Search GitHub issues'
    assert contribution.capabilities == ('search', 'read')
    assert contribution.input_schema == input_schema
    assert contribution.output_schema == output_schema
    assert contribution.safety_metadata == safety_metadata
    assert contribution.safety_metadata is not safety_metadata
    assert contribution.metadata == metadata
    assert contribution.metadata is not metadata
    assert callable(contribution.validate_config)
    assert callable(contribution.create_tool)


def test_provider_contribution_normalizes_and_copies_fields() -> None:
    default_parameters = {'temperature': 0.2}
    metadata = {'vendor': 'litellm'}

    contribution = ProviderContribution(
        name='litellm',
        provider_type='llm',
        description='LiteLLM provider',
        supported_parameters=['model', 'temperature'],
        default_parameters=default_parameters,
        validate_profile=lambda *args, **kwargs: None,
        create_client=lambda *args, **kwargs: object(),
        metadata=metadata,
    )

    assert contribution.name == 'litellm'
    assert contribution.provider_type == 'llm'
    assert contribution.description == 'LiteLLM provider'
    assert contribution.supported_parameters == ('model', 'temperature')
    assert contribution.default_parameters == default_parameters
    assert contribution.default_parameters is not default_parameters
    assert contribution.metadata == metadata
    assert contribution.metadata is not metadata
    assert callable(contribution.validate_profile)
    assert callable(contribution.create_client)


def test_store_contribution_keeps_store_type_and_backend_name_distinct() -> None:
    artifact_store = StoreContribution(
        backend_name='memory',
        store_type='artifact',
        description='Artifact store',
        validate_config=lambda *args, **kwargs: None,
        create_store=lambda *args, **kwargs: object(),
        metadata={'scope': 'artifact'},
    )
    checkpoint_store = StoreContribution(
        backend_name='memory',
        store_type='checkpoint',
        description='Checkpoint store',
        validate_config=lambda *args, **kwargs: None,
        create_store=lambda *args, **kwargs: object(),
        metadata={'scope': 'checkpoint'},
    )

    assert artifact_store.backend_name == 'memory'
    assert artifact_store.store_type == 'artifact'
    assert checkpoint_store.backend_name == 'memory'
    assert checkpoint_store.store_type == 'checkpoint'
    assert artifact_store != checkpoint_store


def test_event_sink_contribution_copies_metadata_and_keeps_hooks() -> None:
    metadata = {'backend': 'stdout'}

    contribution = EventSinkContribution(
        backend_name='stdout',
        description='Stdout sink',
        validate_config=lambda *args, **kwargs: None,
        create_sink=lambda *args, **kwargs: object(),
        metadata=metadata,
    )

    assert contribution.backend_name == 'stdout'
    assert contribution.description == 'Stdout sink'
    assert contribution.metadata == metadata
    assert contribution.metadata is not metadata
    assert callable(contribution.validate_config)
    assert callable(contribution.create_sink)


def test_contribution_metadata_defaults_are_not_shared() -> None:
    first = ToolContribution(name='first')
    second = ToolContribution(name='second')

    assert first.metadata == {}
    assert second.metadata == {}
    assert first.metadata is not second.metadata

    first_provider = ProviderContribution(name='first', provider_type='llm')
    second_provider = ProviderContribution(name='second', provider_type='llm')

    assert first_provider.default_parameters == {}
    assert second_provider.default_parameters == {}
    assert first_provider.metadata is not second_provider.metadata
