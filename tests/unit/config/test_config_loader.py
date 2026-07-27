from __future__ import annotations

import pytest

from cobalt_wren.api.errors import ConfigError
from cobalt_wren.config.loader import load_package_config_from_mapping
from cobalt_wren.config.models import RawPackageConfig


def test_load_package_config_from_mapping_accepts_minimal_payload() -> None:
    raw = load_package_config_from_mapping({"version": 1})

    assert isinstance(raw, RawPackageConfig)
    assert raw.version == 1
    assert raw.environment is None
    assert raw.plugins == {}


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        ({}, "CONFIG_MISSING_VERSION"),
        ({"version": "1"}, "CONFIG_INVALID_VERSION_TYPE"),
        ({"version": 2}, "CONFIG_UNSUPPORTED_VERSION"),
        ({"version": 1, "unknown": True}, "CONFIG_UNKNOWN_TOP_LEVEL_FIELD"),
    ],
)
def test_load_package_config_from_mapping_rejects_invalid_payloads(payload: dict[str, object], code: str) -> None:
    with pytest.raises(ConfigError) as excinfo:
        load_package_config_from_mapping(payload)

    assert excinfo.value.code == code


def test_load_package_config_from_mapping_accepts_known_top_level_fields() -> None:
    raw = load_package_config_from_mapping(
        {
            "version": 1,
            "environment": "staging",
            "plugins": {"enabled": ["alpha"]},
            "providers": {"default": {"provider": "litellm"}},
            "tools": {"allowlist": ["echo"]},
            "stores": {"artifact": {"backend": "memory"}},
            "event_sinks": {"stdout": {"backend": "stdout"}},
            "limits": {"max_steps": 10},
            "observability": {"capture": {"input_summary": True}},
            "safety": {"redaction_enabled": True, "safe_errors": True},
            "metadata": {"team": "platform"},
        }
    )

    assert raw.environment == "staging"
    assert raw.plugins == {"enabled": ["alpha"]}
    assert raw.providers == {"default": {"provider": "litellm"}}


def test_load_package_config_from_mapping_rejects_secret_literal() -> None:
    with pytest.raises(ConfigError) as excinfo:
        load_package_config_from_mapping(
            {
                "version": 1,
                "providers": {
                    "default": {
                        "provider": "litellm",
                        "api_key_env": "sk-xxxx",
                    }
                },
            }
        )

    assert excinfo.value.code == "CONFIG_SECRET_LITERAL"
