"""Architecture guard for graph-local runtime config boundaries."""

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


def test_graph_runtime_does_not_import_service_layer_config() -> None:
    path = Path('src/langgraph_automation/graphs/runtime.py')
    modules = _imported_modules(path)

    offenders = [module for module in modules if module.startswith('langgraph_automation.apps.automation.services')]
    assert offenders == []


def test_graph_config_is_pure_and_graph_local() -> None:
    path = Path('src/langgraph_automation/graphs/config.py')
    modules = _imported_modules(path)

    offenders = [
        module
        for module in modules
        if module.startswith(
            (
                'django',
                'litellm',
                'langgraph_automation.apps.',
                'langgraph_automation.integrations.',
                'langgraph_automation.config',
            )
        )
    ]
    assert offenders == []


def test_workflow_config_does_not_depend_on_graph_runtime_or_concrete_graphs() -> None:
    path = Path('src/langgraph_automation/apps/automation/services/workflow_config.py')
    modules = _imported_modules(path)

    offenders = [module for module in modules if module.startswith('langgraph_automation.graphs')]
    assert offenders == []
