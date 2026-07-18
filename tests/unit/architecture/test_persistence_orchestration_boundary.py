"""Architecture guard for persistence orchestration boundaries."""

from __future__ import annotations

from pathlib import Path


def test_execution_path_does_not_call_artifact_or_checkpoint_store_persistence_methods() -> None:
    paths = (
        Path('src/langgraph_automation/apps/automation/services/runtime.py'),
        Path('src/langgraph_automation/apps/automation/services/execution.py'),
        Path('src/langgraph_automation/apps/automation/services/runs.py'),
        Path('src/langgraph_automation/graphs/runner.py'),
    )

    forbidden_tokens = (
        'artifact_store.put(',
        'checkpoint_store.save(',
        'ArtifactStore.put(',
        'CheckpointStore.save(',
    )

    for path in paths:
        text = path.read_text().lower()
        offenders = [token for token in forbidden_tokens if token.lower() in text]
        assert offenders == [], f'{path} still references persistence write calls: {offenders}'


def test_application_runtime_does_not_directly_construct_concrete_persistence_stores() -> None:
    path = Path('src/langgraph_automation/apps/automation/services/runtime.py')
    text = path.read_text()

    for token in (
        'MemoryArtifactStore(',
        'FilesystemArtifactStore(',
        'MemoryCheckpointStore(',
        'FilesystemCheckpointStore(',
    ):
        assert token not in text, f'{path} still directly constructs concrete persistence stores: {token}'
