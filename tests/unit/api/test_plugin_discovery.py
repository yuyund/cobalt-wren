"""Public optional plugin discovery tests."""
from __future__ import annotations
from dataclasses import dataclass
import pytest
from langgraph_automation.api.errors import PluginResolutionError
from langgraph_automation.api.plugins import DEFAULT_PLUGIN_ENTRY_POINT_GROUP, Plugin, PluginMetadata, discover_plugins

@dataclass(frozen=True)
class FakeEntryPoint:
    name: str
    value: str
    loaded: object
    def load(self) -> object:
        if isinstance(self.loaded, BaseException):
            raise self.loaded
        return self.loaded

class FakeEntryPoints(tuple):
    def select(self, *, group: str):
        assert group == DEFAULT_PLUGIN_ENTRY_POINT_GROUP
        return self

def test_discover_plugins_loads_instances_and_factories(monkeypatch: pytest.MonkeyPatch) -> None:
    first = Plugin(metadata=PluginMetadata(name="a", version="1"))
    second = Plugin(metadata=PluginMetadata(name="b", version="1"))
    entries = FakeEntryPoints((FakeEntryPoint("z", "factory", lambda: second), FakeEntryPoint("a", "instance", first)))
    monkeypatch.setattr("langgraph_automation.api.plugins.importlib_metadata.entry_points", lambda: entries)
    assert discover_plugins() == (first, second)

def test_discover_plugins_wraps_load_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    entries = FakeEntryPoints((FakeEntryPoint("broken", "broken", ValueError("secret detail")),))
    monkeypatch.setattr("langgraph_automation.api.plugins.importlib_metadata.entry_points", lambda: entries)
    with pytest.raises(PluginResolutionError) as excinfo:
        discover_plugins()
    assert excinfo.value.code == "PLUGIN_DISCOVERY_FAILED"
    assert excinfo.value.component == "plugin_discovery"
    assert "secret detail" not in str(excinfo.value)

def test_discover_plugins_rejects_invalid_result(monkeypatch: pytest.MonkeyPatch) -> None:
    entries = FakeEntryPoints((FakeEntryPoint("invalid", "invalid", lambda: object()),))
    monkeypatch.setattr("langgraph_automation.api.plugins.importlib_metadata.entry_points", lambda: entries)
    with pytest.raises(PluginResolutionError) as excinfo:
        discover_plugins()
    assert excinfo.value.code == "PLUGIN_DISCOVERY_INVALID_RESULT"
