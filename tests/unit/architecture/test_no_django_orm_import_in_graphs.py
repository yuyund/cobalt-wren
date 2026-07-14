'''Architecture guard: graphs/ must not import Django ORM models directly.'''

from __future__ import annotations

from pathlib import Path


def test_graphs_do_not_import_automation_models() -> None:
    root = Path('src/langgraph_automation/graphs')
    offenders: list[str] = []
    for path in root.rglob('*.py'):
        text = path.read_text()
        if 'apps.automation.models' in text:
            offenders.append(str(path))
    assert offenders == []
