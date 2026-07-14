'''Architecture guard: web views must not map run services directly.'''

from __future__ import annotations

from pathlib import Path


def test_web_views_do_not_import_run_service_functions_directly() -> None:
    root = Path('src/langgraph_automation/apps/web/views')
    text = '\n'.join(path.read_text() for path in root.rglob('*.py'))
    assert 'start_run' not in text
    assert 'cancel_run' not in text
    assert 'retry_run' not in text
    assert 'resume_run' not in text
