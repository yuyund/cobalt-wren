from types import SimpleNamespace

import pytest

from cobalt_wren.api.errors import PluginResolutionError
from cobalt_wren.api.plugins import PLUGIN_API_VERSION, Plugin, PluginContributions, PluginMetadata, discover_plugins


class FakeEntryPoint:
    name = "future"
    value = "future:create_plugin"
    def load(self):
        return lambda: Plugin(metadata=PluginMetadata(name="future", version="1", metadata={"plugin_api_version": 99}), contributions=PluginContributions())


def test_plugin_api_version_is_public_integer() -> None:
    assert PLUGIN_API_VERSION == 1


def test_incompatible_plugin_api_version_fails_discovery(monkeypatch: pytest.MonkeyPatch) -> None:
    selection = SimpleNamespace(select=lambda **_kwargs: (FakeEntryPoint(),))
    monkeypatch.setattr("cobalt_wren.api.plugins.importlib_metadata.entry_points", lambda: selection)
    with pytest.raises(PluginResolutionError) as exc_info:
        discover_plugins()
    assert exc_info.value.code == "PLUGIN_API_VERSION_INCOMPATIBLE"
