from __future__ import annotations

import pytest

from langgraph_automation.api.errors import ConfigError
from langgraph_automation.config.security import precheck_package_config_mapping


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        ({"safety": {"enabled": False}}, "CONFIG_SAFETY_DISABLED"),
        ({"safety": {"redaction_enabled": False}}, "CONFIG_SAFETY_DISABLED"),
        ({"safety": {"safe_errors": False}}, "CONFIG_SAFETY_DISABLED"),
        ({"tools": {"allow_all_tools": True}}, "CONFIG_ALLOW_ALL_TOOLS_FORBIDDEN"),
        ({"providers": {"default": {"provider": "litellm", "api_key_env": "sk-xxxx"}}}, "CONFIG_SECRET_LITERAL"),
        ({"providers": {"default": {"provider": "litellm", "factory_path": "my.module:create"}}}, "CONFIG_ARBITRARY_IMPORT"),
        ({"safety": {"persist_raw_tool_output": True}}, "CONFIG_UNSAFE_PERSISTENCE"),
    ],
)
def test_precheck_rejects_unsafe_config(payload: dict[str, object], code: str) -> None:
    with pytest.raises(ConfigError) as excinfo:
        precheck_package_config_mapping(payload)

    assert excinfo.value.code == code


def test_precheck_accepts_env_secret_reference() -> None:
    precheck_package_config_mapping(
        {
            "providers": {
                "default": {
                    "provider": "litellm",
                    "api_key_env": "LLM_API_KEY",
                }
            }
        }
    )
