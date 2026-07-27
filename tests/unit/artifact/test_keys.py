"""Artifact storage key validation tests."""

from __future__ import annotations

import pytest

from cobalt_wren.api.errors import ArtifactValidationError
from cobalt_wren.integrations.artifact.base import ArtifactWriteRequest
from cobalt_wren.integrations.artifact.keys import is_safe_storage_key, validate_storage_key
from cobalt_wren.integrations.artifact.memory_store import MemoryArtifactStore


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
    with pytest.raises(ArtifactValidationError):
        store.put(ArtifactWriteRequest(run_id=1, storage_key='/tmp/output.md', body=b'report', name='report', kind='text'))
