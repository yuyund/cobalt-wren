"""Architecture guard for workflow registry composition boundaries."""

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


def test_workflow_catalog_is_the_only_builtin_composition_entrypoint() -> None:
    modules = _imported_modules(Path('src/langgraph_automation/workflows/catalog.py'))
    assert 'langgraph_automation.workflows.reference.llm_echo_summary.definition' in modules
    assert not any(module.startswith('langgraph_automation.graphs') for module in modules)
