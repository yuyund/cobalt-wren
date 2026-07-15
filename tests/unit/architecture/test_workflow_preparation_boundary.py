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
    module = Path('src/langgraph_automation/workflows/prepare.py')
    modules = _imports(module)

    forbidden_prefixes = (
        'langgraph_automation.apps.automation',
        'django',
        'django.conf',
        'django.db',
        'langgraph_automation.graphs.runner',
        'langgraph_automation.graphs.builders',
        'langgraph_automation.config.validator',
        'langgraph_automation.runtime.assembly',
    )

    offenders = [name for name in modules if name.startswith(forbidden_prefixes)]
    assert offenders == []


def test_workflow_preparation_module_can_import_required_internal_boundaries() -> None:
    modules = _imports(Path('src/langgraph_automation/workflows/prepare.py'))

    allowed_prefixes = (
        'langgraph_automation.api.workflow',
        'langgraph_automation.api.errors',
        'langgraph_automation.plugins.registry',
        'langgraph_automation.runtime.dependencies',
        'langgraph_automation.workflows.adapter',
        'langgraph_automation.workflows.requirements',
    )

    assert any(name.startswith(allowed_prefixes) for name in modules)


def test_workflow_related_internal_modules_do_not_import_preparation_layer() -> None:
    for path in (
        Path('src/langgraph_automation/runtime/assembly.py'),
        Path('src/langgraph_automation/config/validator.py'),
        Path('src/langgraph_automation/plugins/registry.py'),
        Path('src/langgraph_automation/api/workflow.py'),
    ):
        modules = _imports(path)
        offenders = [name for name in modules if name == 'langgraph_automation.workflows.prepare']
        assert offenders == [], f'{path} imports workflow preparation unexpectedly'
