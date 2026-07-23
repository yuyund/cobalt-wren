"""Security prechecks for raw package config."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from langgraph_automation.api.errors import ConfigError

_CONFIG_COMPONENT = "config_loader"
_FORBIDDEN_IMPORT_FIELDS = {
    "callable",
    "callable_path",
    "class_path",
    "factory",
    "factory_path",
    "import",
    "import_path",
    "module",
}
_RAW_PERSISTENCE_BYPASS_FLAGS = {
    "disable_redaction",
    "expose_traceback",
    "persist_raw_input",
    "persist_raw_prompt",
    "persist_raw_response",
    "persist_raw_tool_output",
}
_SECRET_LIKE_PREFIXES = ("sk-", "pk-", "rk-", "ghp_", "gho_", "ghs_", "xoxb-", "xoxa-")
_ENV_VAR_NAME_RE = re.compile(r"^[A-Z_][A-Z0-9_]*$")
_CREDENTIAL_URL_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://[^/@:\s]+:[^/@\s]+@")


def precheck_package_config_mapping(data: Mapping[str, Any]) -> None:
    """Reject unsafe raw config shapes before normalization."""

    _scan_mapping(data)

    safety = data.get("safety")
    if isinstance(safety, Mapping):
        _reject_safety_toggle(safety)

    tools = data.get("tools")
    if isinstance(tools, Mapping) and tools.get("allow_all_tools") is True:
        raise _config_error(
            "Configuration is invalid: allow_all_tools is forbidden.",
            code="CONFIG_ALLOW_ALL_TOOLS_FORBIDDEN",
        )


def normalize_secret_reference(value: Any, *, field_name: str) -> str:
    """Normalize an env secret reference to an env var name."""

    if not isinstance(value, str):
        raise _config_error(
            f"Configuration is invalid: {field_name} must reference an environment variable.",
            code="CONFIG_SECRET_LITERAL",
            metadata={"field_name": field_name},
        )

    env_name = value.strip()
    if not _ENV_VAR_NAME_RE.fullmatch(env_name):
        raise _config_error(
            f"Configuration is invalid: {field_name} must reference an environment variable.",
            code="CONFIG_SECRET_LITERAL",
            metadata={"field_name": field_name},
        )
    return env_name


def _scan_mapping(mapping: Mapping[str, Any]) -> None:
    for key, value in mapping.items():
        if key in _FORBIDDEN_IMPORT_FIELDS:
            raise _config_error(
                f"Configuration is invalid: {key} is not allowed.",
                code="CONFIG_ARBITRARY_IMPORT",
                metadata={"field_name": key},
            )
        if key == "allow_all_tools" and value is True:
            raise _config_error(
                "Configuration is invalid: allow_all_tools is forbidden.",
                code="CONFIG_ALLOW_ALL_TOOLS_FORBIDDEN",
                metadata={"field_name": key},
            )
        if key in _RAW_PERSISTENCE_BYPASS_FLAGS and value is True:
            raise _config_error(
                f"Configuration is invalid: {key} is not allowed.",
                code="CONFIG_UNSAFE_PERSISTENCE",
                metadata={"field_name": key},
            )
        if _is_secret_like_literal(value):
            raise _config_error(
                "Configuration is invalid: secret-like literal is not allowed.",
                code="CONFIG_SECRET_LITERAL",
                metadata={"field_name": key},
            )
        if isinstance(value, Mapping):
            _scan_mapping(value)
        elif isinstance(value, (list, tuple)):
            _scan_sequence(value)


def _scan_sequence(sequence: Sequence[Any]) -> None:
    for value in sequence:
        if _is_secret_like_literal(value):
            raise _config_error(
                "Configuration is invalid: secret-like literal is not allowed.",
                code="CONFIG_SECRET_LITERAL",
            )
        if isinstance(value, Mapping):
            _scan_mapping(value)
        elif isinstance(value, (list, tuple)):
            _scan_sequence(value)


def _is_secret_like_literal(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    text = value.strip()
    if not text:
        return False
    if text.startswith(_SECRET_LIKE_PREFIXES):
        return True
    if _CREDENTIAL_URL_RE.match(text):
        return True
    return False


def _reject_safety_toggle(safety: Mapping[str, Any]) -> None:
    if safety.get("enabled") is False:
        raise _config_error(
            "Configuration is invalid: safety cannot be disabled.",
            code="CONFIG_SAFETY_DISABLED",
        )
    if safety.get("redaction_enabled") is False:
        raise _config_error(
            "Configuration is invalid: redaction cannot be disabled.",
            code="CONFIG_SAFETY_DISABLED",
        )
    if safety.get("safe_errors") is False:
        raise _config_error(
            "Configuration is invalid: safe errors cannot be disabled.",
            code="CONFIG_SAFETY_DISABLED",
        )


def _config_error(
    safe_message: str,
    *,
    code: str,
    metadata: dict[str, Any] | None = None,
) -> ConfigError:
    return ConfigError(safe_message, code=code, component=_CONFIG_COMPONENT, metadata=metadata)
