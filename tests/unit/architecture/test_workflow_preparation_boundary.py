"""Architecture guard for workflow preparation boundaries."""

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


def test_workflow_preparation_module_stays_within_internal_boundaries() -> None:
    module = Path('src/cobalt_wren/workflows/prepare.py')
    modules = _imports(module)

    forbidden_prefixes = (
        'cobalt_wren.apps.automation',
        'django',
        'django.conf',
        'django.db',
        'cobalt_wren.graphs.runner',
        'cobalt_wren.graphs.builders',
        'cobalt_wren.config.validator',
        'cobalt_wren.runtime.assembly',
    )

    offenders = [name for name in modules if name.startswith(forbidden_prefixes)]
    assert offenders == []


def test_workflow_preparation_module_can_import_required_internal_boundaries() -> None:
    modules = _imports(Path('src/cobalt_wren/workflows/prepare.py'))

    allowed_prefixes = (
        'cobalt_wren.api.workflow',
        'cobalt_wren.api.errors',
        'cobalt_wren.plugins.registry',
        'cobalt_wren.runtime.dependencies',
        'cobalt_wren.workflows.adapter',
        'cobalt_wren.workflows.requirements',
    )

    assert any(name.startswith(allowed_prefixes) for name in modules)


def test_workflow_related_internal_modules_do_not_import_preparation_layer() -> None:
    for path in (
        Path('src/cobalt_wren/runtime/assembly.py'),
        Path('src/cobalt_wren/config/validator.py'),
        Path('src/cobalt_wren/plugins/registry.py'),
        Path('src/cobalt_wren/api/workflow.py'),
    ):
        modules = _imports(path)
        offenders = [name for name in modules if name == 'cobalt_wren.workflows.prepare']
        assert offenders == [], f'{path} imports workflow preparation unexpectedly'
