"""Architecture guard for plugin public boundaries."""

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


def test_api_plugins_does_not_import_internal_plugin_mechanisms() -> None:
    modules = _imported_modules(Path('src/cobalt_wren/api/plugins.py'))
    allowed_prefixes = (
        'cobalt_wren.api.workflow',
        'cobalt_wren.api.errors',
    )
    offenders = [
        module
        for module in modules
        if module.startswith('cobalt_wren.') and not module.startswith(allowed_prefixes)
    ]
    assert offenders == []


def test_plugin_registry_only_depends_on_public_api_and_errors() -> None:
    modules = _imported_modules(Path('src/cobalt_wren/plugins/registry.py'))

    allowed_prefixes = (
        'cobalt_wren.api.plugins',
        'cobalt_wren.api.workflow',
        'cobalt_wren.api.errors',
        'cobalt_wren.api.errors',
    )
    forbidden_prefixes = (
        'cobalt_wren.apps.automation',
        'cobalt_wren.graphs.runner',
        'cobalt_wren.graphs.builders',
        'cobalt_wren.workflows.catalog',
        'cobalt_wren.config',
        'cobalt_wren.integrations',
        'django.',
    )

    allowed = [module for module in modules if module.startswith(allowed_prefixes)]
    forbidden = [module for module in modules if module.startswith(forbidden_prefixes)]

    assert set(allowed) == {
        'cobalt_wren.api.errors',
        'cobalt_wren.api.plugins',
        'cobalt_wren.api.workflow',
        'cobalt_wren.api.errors',
    }
    assert forbidden == []
