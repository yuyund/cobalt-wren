"""Architecture guard for service-layer workflow integration."""

from __future__ import annotations

import ast
from pathlib import Path


def _imports(path: Path) -> list[str]:
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


def test_workflow_preparation_service_stays_within_allowed_boundaries() -> None:
    module = Path('src/cobalt_wren/apps/automation/services/workflow_preparation.py')
    modules = _imports(module)

    forbidden_prefixes = (
        'cobalt_wren.workflows.prepare',
        'cobalt_wren.workflows.catalog',
        'cobalt_wren.workflows.adapter',
        'cobalt_wren.workflows.requirements',
        'cobalt_wren.plugins.registry',
        'cobalt_wren.runtime.assembly',
        'cobalt_wren.runtime.dependencies',
        'cobalt_wren.config.validator',
        'cobalt_wren.graphs',
    )

    offenders = [name for name in modules if name.startswith(forbidden_prefixes)]
    assert offenders == []


def test_workflow_preparation_service_imports_package_facing_boundary_only() -> None:
    modules = _imports(Path('src/cobalt_wren/apps/automation/services/workflow_preparation.py'))

    expected_prefixes = (
        'cobalt_wren.api.engine',
        'cobalt_wren.api.plugins',
    )

    assert any(name.startswith(expected_prefixes) for name in modules)
