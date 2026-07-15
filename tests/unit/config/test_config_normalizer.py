from __future__ import annotations

import pytest

from langgraph_automation.api.errors import ConfigError
from langgraph_automation.config.loader import load_package_config_from_mapping
from langgraph_automation.config.models import RawPackageConfig, SecretRef
from langgraph_automation.config.normalizer import (
    load_normalized_package_config_from_mapping,
    normalize_package_config,
)


def test_normalize_package_config_applies_defaults() -> None:
    raw = load_package_config_from_mapping({"version": 1})
    normalized = normalize_package_config(raw)

    assert normalized.environment == "default"
    assert normalized.plugins.enabled == ()
    assert normalized.tools.allowlist == ()
    assert normalized.safety.redaction_enabled is True
    assert normalized.safety.safe_errors is True


def test_normalize_package_config_normalizes_nested_sections() -> None:
    normalized = load_normalized_package_config_from_mapping(
        {
            "version": 1,
            "environment": "staging",
            "plugins": {"enabled": ["alpha", "beta"]},
            "providers": {
                "default": {
                    "provider": "litellm",
                    "model": "gpt-4.1-mini",
                    "parameters": {"temperature": 0.2},
                    "api_key_env": "LLM_API_KEY",
                }
            },
            "tools": {"allowlist": ["echo"], "configs": {"echo": {"mode": "safe"}}},
            "stores": {"artifact": {"backend": "memory", "config": {"root": "var/artifacts"}}},
            "event_sinks": {"stdout": {"backend": "stdout", "config": {"format": "json"}}},
            "limits": {"max_steps": 5},
            "observability": {"capture": {"input_summary": True}},
            "safety": {"redaction_enabled": True, "safe_errors": True},
            "metadata": {"team": "platform"},
        }
    )

    assert normalized.environment == "staging"
    assert normalized.plugins.enabled == ("alpha", "beta")
    assert normalized.tools.allowlist == ("echo",)
    assert normalized.tools.configs == {"echo": {"mode": "safe"}}
    assert normalized.providers["default"].provider == "litellm"
    assert normalized.providers["default"].model == "gpt-4.1-mini"
    assert normalized.providers["default"].parameters == {"temperature": 0.2}
    assert normalized.providers["default"].secrets == {"api_key": SecretRef(source="env", name="LLM_API_KEY")}
    assert normalized.stores["artifact"].backend == "memory"
    assert normalized.stores["artifact"].config == {"root": "var/artifacts"}
    assert normalized.event_sinks["stdout"].backend == "stdout"
    assert normalized.event_sinks["stdout"].config == {"format": "json"}
    assert normalized.limits.values == {"max_steps": 5}
    assert normalized.observability == {"capture": {"input_summary": True}}
    assert normalized.metadata == {"team": "platform"}


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        (RawPackageConfig(version=1, plugins={"enabled": ["alpha", "alpha"]}), "CONFIG_DUPLICATE_ENABLED_PLUGIN"),
        (RawPackageConfig(version=1, tools={"allowlist": ["echo", "echo"]}), "CONFIG_DUPLICATE_TOOL_ALLOWLIST"),
        (RawPackageConfig(version=1, safety={"enabled": False}), "CONFIG_SAFETY_DISABLED"),
        (RawPackageConfig(version=1, safety={"redaction_enabled": False}), "CONFIG_SAFETY_DISABLED"),
        (RawPackageConfig(version=1, safety={"safe_errors": False}), "CONFIG_SAFETY_DISABLED"),
        (RawPackageConfig(version=1, tools={"allow_all_tools": True}), "CONFIG_ALLOW_ALL_TOOLS_FORBIDDEN"),
        (
            RawPackageConfig(version=1, providers={"default": {"provider": "litellm", "factory_path": "my.module:create"}}),
            "CONFIG_ARBITRARY_IMPORT",
        ),
        (RawPackageConfig(version=1, safety={"persist_raw_response": True}), "CONFIG_UNSAFE_PERSISTENCE"),
        (RawPackageConfig(version=1, providers={"default": {"provider": "litellm", "api_key_env": "sk-xxxx"}}), "CONFIG_SECRET_LITERAL"),
    ],
)
def test_normalize_package_config_rejects_unsafe_payloads(payload: RawPackageConfig, code: str) -> None:
    with pytest.raises(ConfigError) as excinfo:
        normalize_package_config(payload)

    assert excinfo.value.code == code
