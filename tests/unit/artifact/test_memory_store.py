"""Memory artifact store tests."""

from __future__ import annotations

from langgraph_automation.integrations.artifact.base import ArtifactWriteResult
from langgraph_automation.integrations.artifact.memory_store import MemoryArtifactStore


def test_memory_artifact_store_put_get_and_list_for_run() -> None:
    store = MemoryArtifactStore()
    artifact = ArtifactWriteResult(
        storage_key='run-123/output.md',
        name='report',
        kind='text',
        content_type='text/markdown',
        size=12,
        metadata={'run_id': 123, 'phase': 'run'},
    )

    written = store.put(artifact)

    assert written.storage_key == 'run-123/output.md'
    assert store.get('run-123/output.md') == written
    assert store.list_for_run(123) == [written]
