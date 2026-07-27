"""Architecture guards for workflow OSS integration contracts."""

from __future__ import annotations

import ast
from pathlib import Path


def _imports(path: str) -> list[str]:
    tree = ast.parse(Path(path).read_text())
    result: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            result.append(node.module)
    return result


def _is_external_framework(module: str) -> bool:
    return module in {"langgraph", "prefect", "llama_index"} or module.startswith(
        ("langgraph.", "prefect.", "llama_index.")
    )


def test_public_integration_facade_has_no_framework_or_internal_dependencies() -> None:
    imports = _imports("src/cobalt_wren/api/integrations.py")
    offenders = [
        item
        for item in imports
        if _is_external_framework(item) or item.startswith(("django", "cobalt_wren."))
    ]
    assert offenders == []


def test_workflow_integration_registry_does_not_depend_on_control_plane_or_frameworks() -> None:
    imports = _imports("src/cobalt_wren/integrations/workflows/registry.py")
    offenders = [
        item
        for item in imports
        if _is_external_framework(item)
        or item.startswith((
            "django",
            "cobalt_wren.apps",
            "cobalt_wren.workflows.adapter",
        ))
    ]
    assert offenders == []
