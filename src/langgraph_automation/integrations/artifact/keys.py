"""Opaque storage key validation for artifact metadata."""

from __future__ import annotations

import re

_WINDOWS_ABSOLUTE_PATH = re.compile(r"(?i)^[a-z]:[\\/]")


def is_safe_storage_key(storage_key: str) -> bool:
    """Return True when the storage key is an opaque relative key."""

    if not storage_key or storage_key.strip() != storage_key:
        return False
    if storage_key.startswith(("/", "\\", "~", "//")):
        return False
    if _WINDOWS_ABSOLUTE_PATH.match(storage_key):
        return False
    if ":" in storage_key or "\\" in storage_key:
        return False

    parts = storage_key.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        return False
    return True


def validate_storage_key(storage_key: str) -> str:
    """Return the storage key when safe, otherwise raise ValueError."""

    if not is_safe_storage_key(storage_key):
        raise ValueError(f"unsafe artifact storage key: {storage_key!r}")
    return storage_key
