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


def test_graph_registry_does_not_import_concrete_workflows() -> None:
    modules = _imported_modules(Path('src/langgraph_automation/graphs/registry.py'))
    offenders = [module for module in modules if module.startswith('langgraph_automation.workflows.')]
    assert offenders == []


def test_graph_builders_do_not_import_concrete_workflows() -> None:
    modules = _imported_modules(Path('src/langgraph_automation/graphs/builders.py'))
    offenders = [module for module in modules if module.startswith('langgraph_automation.workflows.')]
    assert offenders == []


def test_workflow_catalog_is_the_only_builtin_composition_entrypoint() -> None:
    modules = _imported_modules(Path('src/langgraph_automation/workflows/catalog.py'))
    assert 'langgraph_automation.workflows.reference.llm_echo_summary.definition' in modules
    assert 'langgraph_automation.graphs.registry' in modules
