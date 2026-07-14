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
    modules = _imported_modules(Path('src/langgraph_automation/api/plugins.py'))
    offenders = [module for module in modules if module.startswith('langgraph_automation.')]
    assert offenders == []


def test_plugin_registry_only_depends_on_public_api_and_errors() -> None:
    modules = _imported_modules(Path('src/langgraph_automation/plugins/registry.py'))

    allowed_prefixes = (
        'langgraph_automation.api.plugins',
        'langgraph_automation.api.errors',
    )
    forbidden_prefixes = (
        'langgraph_automation.apps.automation',
        'langgraph_automation.graphs.runner',
        'langgraph_automation.graphs.builders',
        'langgraph_automation.workflows.catalog',
        'langgraph_automation.config',
        'langgraph_automation.integrations',
        'django.',
    )

    allowed = [module for module in modules if module.startswith(allowed_prefixes)]
    forbidden = [module for module in modules if module.startswith(forbidden_prefixes)]

    assert set(allowed) == {'langgraph_automation.api.errors', 'langgraph_automation.api.plugins'}
    assert forbidden == []
