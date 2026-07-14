'''Architecture guard: templates must not introspect Django model metadata.'''

from __future__ import annotations

from pathlib import Path


def test_templates_do_not_use_meta_introspection() -> None:
    root = Path('src/langgraph_automation/apps/web/templates')
    offenders: list[str] = []
    for path in root.rglob('*.html'):
        if '_meta' in path.read_text():
            offenders.append(str(path))
    assert offenders == []
