"""Runtime assembler boundary tests."""

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


def test_runtime_package_does_not_import_forbidden_boundaries() -> None:
    forbidden_prefixes = (
        'langgraph_automation.plugins.registry',
        'langgraph_automation.apps.automation',
        'langgraph_automation.graphs.runner',
        'langgraph_automation.graphs.builders',
        'langgraph_automation.workflows.catalog',
        'langgraph_automation.integrations.',
        'django',
    )

    for relative in (
        Path('src/langgraph_automation/runtime/__init__.py'),
        Path('src/langgraph_automation/runtime/dependencies.py'),
        Path('src/langgraph_automation/runtime/context.py'),
        Path('src/langgraph_automation/runtime/secrets.py'),
        Path('src/langgraph_automation/runtime/assembly.py'),
    ):
        modules = _imported_modules(relative)
        offenders = [module for module in modules if module.startswith(forbidden_prefixes)]
        assert offenders == [], f'{relative} imports forbidden modules: {offenders}'


def test_runtime_package_may_import_public_facades_only() -> None:
    modules = []
    for relative in (
        Path('src/langgraph_automation/runtime/context.py'),
        Path('src/langgraph_automation/runtime/secrets.py'),
        Path('src/langgraph_automation/runtime/assembly.py'),
    ):
        modules.extend(_imported_modules(relative))

    assert any(module.startswith('langgraph_automation.api.errors') for module in modules)
    assert any(module.startswith('langgraph_automation.config.models') for module in modules)
