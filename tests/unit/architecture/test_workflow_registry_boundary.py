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


def test_workflow_catalog_does_not_import_examples_or_implementations() -> None:
    modules = _imported_modules(Path("src/cobalt_wren/workflows/catalog.py"))

    assert "cobalt_wren.api.plugins" in modules
    assert "cobalt_wren.plugins.registry" in modules
    assert not any("reference" in module for module in modules)
    assert not any("examples" in module for module in modules)
    assert not any(module.startswith("cobalt_wren.graphs") for module in modules)
    assert not any(module.startswith("cobalt_wren.native") for module in modules)
