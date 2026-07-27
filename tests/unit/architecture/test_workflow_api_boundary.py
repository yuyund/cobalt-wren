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
        "cobalt_wren.runtime",
        "cobalt_wren.plugins.registry",
        "cobalt_wren.config.validator",
        "cobalt_wren.graphs.runner",
        "cobalt_wren.graphs.builders",
        "cobalt_wren.apps.automation",
        "cobalt_wren.workflows.catalog",
        "django",
    )

    modules = _imported_modules(Path("src/cobalt_wren/api/workflow.py"))
    offenders = [module for module in modules if module.startswith(forbidden_prefixes)]
    assert offenders == []


def test_plugin_registry_may_import_workflow_facade_but_not_runtime() -> None:
    modules = _imported_modules(Path("src/cobalt_wren/plugins/registry.py"))

    assert any(module.startswith("cobalt_wren.api.workflow") for module in modules)
    assert not any(module.startswith("cobalt_wren.runtime") for module in modules)
