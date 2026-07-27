"""Architecture guard for LLM config parsing and adapter boundaries."""

from __future__ import annotations

import ast
from pathlib import Path

BANNED_WORKFLOW_CONFIG_IMPORTS = (
    'django.db',
    'cobalt_wren.apps.automation.models',
    'cobalt_wren.graphs.builders',
    'cobalt_wren.graphs.nodes',
    'cobalt_wren.integrations.llm.litellm_client',
    'cobalt_wren.integrations.tools.safe_tools',
    'cobalt_wren.config.settings',
)


def _imported_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text())
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.append(node.module)
    return modules


def test_litellm_client_does_not_import_django_or_graphs() -> None:
    path = Path('src/cobalt_wren/integrations/llm/litellm_client.py')
    modules = _imported_modules(path)

    offenders = [module for module in modules if module.startswith(('django.db', 'cobalt_wren.apps.automation', 'cobalt_wren.graphs'))]
    assert offenders == []


def test_litellm_is_not_a_runtime_dependency() -> None:
    import tomllib

    data = tomllib.loads(Path("pyproject.toml").read_text())
    assert not any(
        dependency.startswith("litellm")
        for dependency in data["project"]["dependencies"]
    )
    assert any(
        dependency.startswith("litellm")
        for dependency in data["project"]["optional-dependencies"]["dev"]
    )
