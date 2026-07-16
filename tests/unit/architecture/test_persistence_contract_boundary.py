"""Architecture guard for persistence contract boundaries."""

from __future__ import annotations

from pathlib import Path

from tests.support.import_scan import collect_import_targets


def test_graphs_runner_does_not_import_concrete_persistence_backends_or_django_models() -> None:
    targets = collect_import_targets(Path('src/langgraph_automation/graphs/runner.py'))
    offenders = [
        target
        for target in targets
        if target.startswith(
            (
                'langgraph_automation.integrations.artifact.memory_store',
                'langgraph_automation.integrations.checkpoint.memory_store',
                'langgraph_automation.apps.automation.models',
                'django',
            )
        )
    ]
    assert offenders == []

