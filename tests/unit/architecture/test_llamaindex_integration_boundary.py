"""Architecture guards for the official LlamaIndex Workflows integration."""

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


def test_llamaindex_provider_does_not_import_control_plane_or_django() -> None:
    imports = _imports(
        "src/cobalt_wren/integrations/workflows/llamaindex_provider.py"
    )
    offenders = [
        item
        for item in imports
        if item.startswith(("django", "cobalt_wren.apps.automation"))
    ]
    assert offenders == []


def test_llamaindex_framework_imports_are_isolated_to_provider_and_helper() -> None:
    foundation_files = (
        "src/cobalt_wren/integrations/workflows/definitions.py",
        "src/cobalt_wren/integrations/workflows/registry.py",
        "src/cobalt_wren/apps/automation/services/integration_projections.py",
        "src/cobalt_wren/apps/automation/ui/integration_actions.py",
    )
    offenders: list[tuple[str, str]] = []
    for path in foundation_files:
        for module in _imports(path):
            if module == "workflows" or module.startswith("workflows."):
                offenders.append((path, module))
    assert offenders == []
