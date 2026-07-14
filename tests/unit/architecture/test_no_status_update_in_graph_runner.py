'''Architecture guard: graph runner must not update Run.status directly.'''

from __future__ import annotations

from pathlib import Path


def test_graph_runner_does_not_update_run_status() -> None:
    text = Path('src/langgraph_automation/graphs/runner.py').read_text()
    assert 'Run.status' not in text
    assert '.save(update_fields' not in text
