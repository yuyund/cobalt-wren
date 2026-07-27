"""Architecture guards for the official LangGraph integration."""

from __future__ import annotations

import ast
from pathlib import Path


def _imports(path: str) -> list[str]:
    tree = ast.parse(Path(path).read_text())
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
    return modules


def test_central_definitions_do_not_import_target_frameworks() -> None:
    imports = _imports("src/cobalt_wren/integrations/workflows/definitions.py")
    assert not any(
        item == "langgraph"
        or item.startswith("langgraph.")
        or item == "workflows"
        or item.startswith("workflows.")
        for item in imports
    )


def test_langgraph_provider_does_not_import_control_plane_or_django() -> None:
    imports = _imports("src/cobalt_wren/integrations/workflows/langgraph_provider.py")
    offenders = [
        item
        for item in imports
        if item.startswith(("django", "cobalt_wren.apps.automation"))
    ]
    assert offenders == []
