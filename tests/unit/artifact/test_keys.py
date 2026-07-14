"""Artifact storage key validation tests."""

from __future__ import annotations

import pytest

from langgraph_automation.integrations.artifact.base import ArtifactWriteResult
from langgraph_automation.integrations.artifact.keys import is_safe_storage_key, validate_storage_key
from langgraph_automation.integrations.artifact.memory_store import MemoryArtifactStore


@pytest.mark.parametrize(
    'storage_key',
    [
        'run-123/output.md',
        'artifacts/run-123/output.md',
        'local/run-123/output.md',
        'artifact-run-123-output-md',
    ],
)
def test_is_safe_storage_key_accepts_opaque_relative_keys(storage_key: str) -> None:
    assert is_safe_storage_key(storage_key) is True
    assert validate_storage_key(storage_key) == storage_key


@pytest.mark.parametrize(
    'storage_key',
    [
        '',
        '/tmp/output.md',
        '~/output.md',
        '../secret.txt',
        'C:/Users/me/output.md',
        'C:\\Users\\me\\output.md',
        '//server/share/output.md',
        'folder/../secret.txt',
        'folder//output.md',
    ],
)
def test_validate_storage_key_rejects_unsafe_keys(storage_key: str) -> None:
    assert is_safe_storage_key(storage_key) is False
    with pytest.raises(ValueError):
        validate_storage_key(storage_key)


def test_memory_artifact_store_rejects_unsafe_storage_keys() -> None:
    store = MemoryArtifactStore()
    artifact = ArtifactWriteResult(storage_key='/tmp/output.md', name='report', kind='text')

    with pytest.raises(ValueError):
        store.put(artifact)
