'''Architecture guard: UI builders must not introspect obj.__dict__.'''

from __future__ import annotations

from pathlib import Path


def test_ui_builders_do_not_use_obj_dict() -> None:
    text = Path('src/cobalt_wren/apps/automation/ui/builders.py').read_text()
    assert '__dict__' not in text
