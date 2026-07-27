"""Shared redaction helpers for secrets, paths, and nested payloads."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

REDACTED_VALUE = "***REDACTED***"
TRUNCATED_VALUE = "***TRUNCATED***"

SENSITIVE_KEY_PARTS = (
    "secret",
    "token",
    "api_key",
    "apikey",
    "password",
    "authorization",
    "access_token",
    "refresh_token",
    "credential",
    "credentials",
    "private_key",
    "path",
    "file_path",
    "absolute_path",
)

_BEARER_PATTERN=re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{8,}")
_UNIX_PATH_PATTERN=re.compile(r"(?<!:)(?<!\w)/\S+")
_WINDOWS_PATH_PATTERN=re.compile(r"(?i)\b[a-z]:[\\/]\S+")
_HOME_PATH_PATTERN=re.compile(r"~[\\/]\S+")
_UNC_PATH_PATTERN=re.compile(r"\\\\\S+")
_KEY_VALUE_PATTERN = re.compile(
    r"(?i)\b(?:secret|token|api[_-]?key|apikey|password|authorization|access[_-]?token|refresh[_-]?token|credential|credentials|private[_-]?key|path|file[_-]?path|absolute[_-]?path)\b\s*[:=]\s*([^\s,;]+)"
)


def is_sensitive_key(name: str) -> bool:
    """Return True when a key name should be redacted."""

    lowered = name.lower()
    return any(part in lowered for part in SENSITIVE_KEY_PARTS)


def redact_text(text: str) -> str:
    """Redact obvious secret-bearing substrings from text."""

    redacted = _BEARER_PATTERN.sub(f"Bearer {REDACTED_VALUE}", text)
    redacted = _UNIX_PATH_PATTERN.sub(REDACTED_VALUE, redacted)
    redacted = _WINDOWS_PATH_PATTERN.sub(REDACTED_VALUE, redacted)
    redacted = _HOME_PATH_PATTERN.sub(REDACTED_VALUE, redacted)
    redacted = _UNC_PATH_PATTERN.sub(REDACTED_VALUE, redacted)

    def _replace(match: re.Match[str]) -> str:
        matched = match.group(0)
        if ':' in matched:
            prefix = matched.split(':', 1)[0]
        elif '=' in matched:
            prefix = matched.split('=', 1)[0]
        else:
            prefix = matched
        return f"{prefix}={REDACTED_VALUE}"

    return _KEY_VALUE_PATTERN.sub(_replace, redacted)


def _redact_sequence(value: Sequence[Any], *, max_depth: int, _depth: int) -> Sequence[Any]:
    items = [redact_value(item, max_depth=max_depth, _depth=_depth + 1) for item in value]
    if isinstance(value, tuple):
        return tuple(items)
    return list(items)


def _redact_mapping(value: Mapping[str, Any], *, max_depth: int, _depth: int) -> dict[str, Any]:
    if _depth >= max_depth:
        return {str(key): TRUNCATED_VALUE for key in value.keys()}

    redacted: dict[str, Any] = {}
    for key, nested_value in value.items():
        key_name = str(key)
        if is_sensitive_key(key_name):
            redacted[key_name] = REDACTED_VALUE
            continue
        redacted[key_name] = redact_value(nested_value, key_name=key_name, max_depth=max_depth, _depth=_depth + 1)
    return redacted


def redact_value(value: Any, *, key_name: str | None = None, max_depth: int = 4, _depth: int = 0) -> Any:
    """Redact a nested value without mutating the input object."""

    if key_name is not None and is_sensitive_key(key_name):
        return REDACTED_VALUE
    if _depth >= max_depth:
        if isinstance(value, Mapping):
            return {str(key): TRUNCATED_VALUE for key in value.keys()}
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            return [TRUNCATED_VALUE for _ in value]
        if isinstance(value, str):
            return TRUNCATED_VALUE
        return TRUNCATED_VALUE
    if isinstance(value, Mapping):
        return _redact_mapping(value, max_depth=max_depth, _depth=_depth)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return _redact_sequence(value, max_depth=max_depth, _depth=_depth)
    if isinstance(value, str):
        return redact_text(value)
    return value


def redact_mapping(mapping: Mapping[str, Any], *, max_depth: int = 4) -> dict[str, Any]:
    """Redact a mapping recursively."""

    return _redact_mapping(mapping, max_depth=max_depth, _depth=0)
