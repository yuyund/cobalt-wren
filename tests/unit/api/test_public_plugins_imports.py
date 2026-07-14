"""Public plugin facade import coverage."""

from __future__ import annotations


def test_public_plugins_api_exports() -> None:
    from langgraph_automation.api.plugins import (
        EventSinkContribution,
        Plugin,
        PluginContributions,
        PluginMetadata,
        ProviderContribution,
        StoreContribution,
        ToolContribution,
    )

    assert Plugin is not None
    assert PluginMetadata is not None
    assert PluginContributions is not None
    assert ToolContribution is not None
    assert ProviderContribution is not None
    assert StoreContribution is not None
    assert EventSinkContribution is not None


def test_public_plugins_api_all() -> None:
    import langgraph_automation.api.plugins as plugins_api

    assert set(plugins_api.__all__) == {
        'Plugin',
        'PluginMetadata',
        'PluginContributions',
        'ToolContribution',
        'ProviderContribution',
        'StoreContribution',
        'EventSinkContribution',
    }
