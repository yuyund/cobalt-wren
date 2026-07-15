"""Architecture guard for workflow facade boundaries."""

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


def test_api_workflow_does_not_import_runtime_or_registry_boundaries() -> None:
    forbidden_prefixes = (
        "langgraph_automation.runtime",
        "langgraph_automation.plugins.registry",
        "langgraph_automation.config.validator",
        "langgraph_automation.graphs.runner",
        "langgraph_automation.graphs.builders",
        "langgraph_automation.apps.automation",
        "langgraph_automation.workflows.catalog",
        "django",
    )

    modules = _imported_modules(Path("src/langgraph_automation/api/workflow.py"))
    offenders = [module for module in modules if module.startswith(forbidden_prefixes)]
    assert offenders == []


def test_plugin_registry_may_import_workflow_facade_but_not_runtime() -> None:
    modules = _imported_modules(Path("src/langgraph_automation/plugins/registry.py"))

    assert any(module.startswith("langgraph_automation.api.workflow") for module in modules)
    assert not any(module.startswith("langgraph_automation.runtime") for module in modules)
