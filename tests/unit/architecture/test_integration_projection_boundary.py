"""Architecture guards for integration projection persistence and rendering."""

from __future__ import annotations

import ast
from pathlib import Path


FOUNDATION_FILES = (
    "src/cobalt_wren/apps/automation/models/integration_projection.py",
    "src/cobalt_wren/apps/automation/services/integration_projections.py",
    "src/cobalt_wren/integrations/observability/projections.py",
    "src/cobalt_wren/apps/automation/ui/specs.py",
    "src/cobalt_wren/apps/automation/ui/builders.py",
    "src/cobalt_wren/apps/web/templates/dynamic/detail.html",
)


def _imports(path: str) -> list[str]:
    if not path.endswith(".py"):
        return []
    tree = ast.parse(Path(path).read_text())
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
    return modules


def test_projection_foundation_does_not_import_workflow_frameworks() -> None:
    offenders: list[tuple[str, str]] = []
    for path in FOUNDATION_FILES:
        for module in _imports(path):
            if module in {"langgraph", "prefect", "llama_index"} or module.startswith(
                ("langgraph.", "prefect.", "llama_index.")
            ):
                offenders.append((path, module))
    assert offenders == []


def test_projection_foundation_has_no_framework_specific_branch_or_schema() -> None:
    offenders: list[str] = []
    framework_tokens = (
        '"langgraph"',
        "'langgraph'",
        "langgraph.",
        '"prefect"',
        "'prefect'",
        "prefect.",
        '"llama_index"',
        "'llama_index'",
        "llama_index.",
    )
    for path in FOUNDATION_FILES:
        text = Path(path).read_text().lower().replace("cobalt_wren", "package")
        for token in framework_tokens:
            if token in text:
                offenders.append(f"{path}:{token}")
    assert offenders == []
