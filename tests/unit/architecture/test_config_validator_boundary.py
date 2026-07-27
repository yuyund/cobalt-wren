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
    path = Path('src/cobalt_wren/config/validator.py')
    modules = _imported_modules(path)

    allowed_prefixes = (
        'cobalt_wren.config.models',
        'cobalt_wren.plugins.registry',
        'cobalt_wren.api.errors',
        'cobalt_wren.api.plugins',
    )
    forbidden_prefixes = (
        'cobalt_wren.apps.automation',
        'cobalt_wren.graphs.runner',
        'cobalt_wren.graphs.builders',
        'cobalt_wren.workflows.catalog',
        'cobalt_wren.integrations.',
        'django',
    )

    offenders = [module for module in modules if module.startswith(forbidden_prefixes)]
    assert offenders == [], f'{path} imports forbidden modules: {offenders}'
    assert any(module.startswith(allowed_prefixes) for module in modules)
