"""Architecture guard for config validator boundaries."""

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


def test_config_validator_module_imports_only_allowed_boundaries() -> None:
    path = Path('src/langgraph_automation/config/validator.py')
    modules = _imported_modules(path)

    allowed_prefixes = (
        'langgraph_automation.config.models',
        'langgraph_automation.plugins.registry',
        'langgraph_automation.api.errors',
        'langgraph_automation.api.plugins',
    )
    forbidden_prefixes = (
        'langgraph_automation.apps.automation',
        'langgraph_automation.graphs.runner',
        'langgraph_automation.graphs.builders',
        'langgraph_automation.workflows.catalog',
        'langgraph_automation.integrations.',
        'django',
    )

    offenders = [module for module in modules if module.startswith(forbidden_prefixes)]
    assert offenders == [], f'{path} imports forbidden modules: {offenders}'
    assert any(module.startswith(allowed_prefixes) for module in modules)
