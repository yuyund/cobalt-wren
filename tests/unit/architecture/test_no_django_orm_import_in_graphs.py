"""Architecture guard: graphs/ must not import Django ORM models or services directly."""

from __future__ import annotations

import ast
from pathlib import Path

def _imported_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text())
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.append(node.module)
    return modules


def test_graphs_do_not_import_django_orm_or_automation_models() -> None:
    offenders: list[str] = []
    for path in Path('src/langgraph_automation/graphs').rglob('*.py'):
        for module in _imported_modules(path):
            if module.startswith(('django.db', 'langgraph_automation.apps.automation.models', 'langgraph_automation.apps.automation.services')):
                offenders.append(f'{path}:{module}')
                break
    assert offenders == []
