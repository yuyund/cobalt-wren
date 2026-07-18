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
