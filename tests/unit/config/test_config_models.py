from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from cobalt_wren.config.models import (
    FilesystemArtifactStoreSettings,
    FilesystemCheckpointStoreSettings,
    EventSinkBackendConfig,
    LimitsConfig,
    NormalizedPackageConfig,
    MemoryArtifactStoreSettings,
    MemoryCheckpointStoreSettings,
    PluginsConfig,
    ProviderProfileConfig,
    RawPackageConfig,
    SafetyConfig,
    SecretRef,
    StoreBackendConfig,
    ToolsConfig,
)


def test_raw_package_config_copies_mappings_and_is_frozen() -> None:
    plugins = {"enabled": ["alpha"]}
    providers = {"default": {"provider": "litellm"}}
    raw = RawPackageConfig(
        version=1,
        environment="test",
        plugins=plugins,
        providers=providers,
        tools={"allowlist": ["echo"]},
        stores={"artifact": {"backend": "memory"}},
        event_sinks={"stdout": {"backend": "stdout"}},
        limits={"max_steps": 5},
        observability={"capture": {"input_summary": True}},
        safety={"redaction_enabled": True, "safe_errors": True},
        metadata={"team": "platform"},
    )

    assert raw.plugins == plugins
    assert raw.providers == providers
    assert raw.plugins is not plugins
    assert raw.providers is not providers
    with pytest.raises(FrozenInstanceError):
        raw.version = 2  # type: ignore[misc]


def test_support_models_normalize_iterables_and_copy_mappings() -> None:
    plugins = PluginsConfig(enabled=["alpha", "beta"])
    tools = ToolsConfig(allowlist=["echo"], configs={"echo": {"mode": "safe"}})
    safety = SafetyConfig()
    limits = LimitsConfig(values={"max_steps": 3})
    provider = ProviderProfileConfig(
        provider="litellm",
        model="gpt-4.1-mini",
        parameters={"temperature": 0.2},
        secrets={"api_key": SecretRef(source="env", name="LLM_API_KEY")},
        metadata={"tier": "default"},
    )
    store = StoreBackendConfig(backend="memory", config={"root": "var/artifacts"}, metadata={"kind": "artifact"})
    sink = EventSinkBackendConfig(backend="stdout", config={"format": "json"}, metadata={"sink": "stdout"})

    assert plugins.enabled == ("alpha", "beta")
    assert tools.allowlist == ("echo",)
    assert tools.configs == {"echo": {"mode": "safe"}}
    assert safety.redaction_enabled is True
    assert safety.safe_errors is True
    assert limits.values == {"max_steps": 3}
    assert provider.secrets == {"api_key": SecretRef(source="env", name="LLM_API_KEY")}
    assert provider.parameters == {"temperature": 0.2}
    assert store.config == {"root": "var/artifacts"}
    assert sink.config == {"format": "json"}


def test_normalized_package_config_copies_mappings() -> None:
    normalized = NormalizedPackageConfig(
        version=1,
        environment="default",
        plugins=PluginsConfig(enabled=("alpha",)),
        providers={"default": ProviderProfileConfig(provider="litellm")},
        tools=ToolsConfig(),
        stores={"artifact": StoreBackendConfig(backend="memory")},
        event_sinks={"stdout": EventSinkBackendConfig(backend="stdout")},
        limits=LimitsConfig(values={"max_steps": 3}),
        observability={"capture": {"input_summary": True}},
        safety=SafetyConfig(),
        metadata={"team": "platform"},
        checkpoint_store=MemoryCheckpointStoreSettings(),
    )

    assert normalized.providers == {"default": ProviderProfileConfig(provider="litellm")}
    assert normalized.stores == {"artifact": StoreBackendConfig(backend="memory")}
    assert normalized.event_sinks == {"stdout": EventSinkBackendConfig(backend="stdout")}
    assert normalized.observability == {"capture": {"input_summary": True}}
    assert normalized.metadata == {"team": "platform"}
    assert normalized.checkpoint_store == MemoryCheckpointStoreSettings()


def test_checkpoint_store_settings_are_frozen_and_hide_root() -> None:
    memory = MemoryCheckpointStoreSettings()
    filesystem = FilesystemCheckpointStoreSettings(root=Path("/srv/private/checkpoints"))

    assert memory.backend == "memory"
    assert filesystem.backend == "filesystem"
    assert filesystem.root == Path("/srv/private/checkpoints")
    assert "/srv/private/checkpoints" not in repr(filesystem)

    with pytest.raises(FrozenInstanceError):
        filesystem.backend = "memory"  # type: ignore[misc]


def test_artifact_store_settings_are_frozen_and_hide_sensitive_root() -> None:
    memory = MemoryArtifactStoreSettings()
    filesystem = FilesystemArtifactStoreSettings(root=Path("/srv/private/artifacts"))

    assert memory.backend == "memory"
    assert filesystem.backend == "filesystem"
    assert filesystem.root == Path("/srv/private/artifacts")
    assert "/srv/private/artifacts" not in repr(filesystem)

    with pytest.raises(FrozenInstanceError):
        filesystem.backend = "memory"  # type: ignore[misc]
