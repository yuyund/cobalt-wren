"""Architecture guards for common integration action routing."""

from __future__ import annotations

import ast
from pathlib import Path


FILES = (
    "src/cobalt_wren/apps/automation/ui/integration_actions.py",
    "src/cobalt_wren/apps/automation/ui/actions.py",
    "src/cobalt_wren/apps/web/access.py",
)


def _imports(path: str) -> list[str]:
    tree = ast.parse(Path(path).read_text())
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
    return modules


def test_common_action_router_does_not_import_workflow_frameworks() -> None:
    offenders: list[tuple[str, str]] = []
    for path in FILES:
        for module in _imports(path):
            if module in {"langgraph", "prefect", "llama_index"} or module.startswith(
                ("langgraph.", "prefect.", "llama_index.")
            ):
                offenders.append((path, module))
    assert offenders == []


def test_common_action_router_has_no_framework_specific_schema_or_branch() -> None:
    offenders: list[str] = []
    tokens = ("langgraph.", '"langgraph"', "'langgraph'", "prefect.", "llama_index.")
    for path in FILES:
        text = Path(path).read_text().lower().replace("cobalt_wren", "package")
        for token in tokens:
            if token in text:
                offenders.append(f"{path}:{token}")
    assert offenders == []
