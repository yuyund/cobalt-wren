"""Architecture guard for application workflow readiness boundaries."""

from __future__ import annotations

import ast
from pathlib import Path


def _imported_modules(path: Path) -> list[str]:
    if not path.exists():
        return []
    tree = ast.parse(path.read_text())
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.append(node.module)
    return modules


def test_application_workflow_packages_do_not_import_control_plane_or_runtime_boundaries() -> None:
    application_root = Path('src/langgraph_automation/workflows/applications')
    if not application_root.exists():
        return

    forbidden_prefixes = (
        'langgraph_automation.apps.automation',
        'langgraph_automation.plugins.registry',
        'langgraph_automation.runtime.assembly',
        'langgraph_automation.config.validator',
        'langgraph_automation.workflows.catalog',
        'langgraph_automation.workflows.reference',
        'django',
        'django.conf',
        'django.db',
    )

    for path in application_root.rglob('*.py'):
        modules = _imported_modules(path)
        offenders = [module for module in modules if module.startswith(forbidden_prefixes)]
        assert offenders == [], f'{path} imports forbidden modules: {offenders}'
