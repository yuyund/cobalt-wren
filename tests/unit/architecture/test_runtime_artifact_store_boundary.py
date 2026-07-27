"""Architecture guard for the canonical artifact store builder."""

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


def test_runtime_artifact_store_builder_does_not_import_forbidden_boundaries() -> None:
    path = Path("src/cobalt_wren/runtime/artifact_store.py")
    modules = _imported_modules(path)

    forbidden_prefixes = (
        "django",
        "cobalt_wren.apps.automation",
        "cobalt_wren.graphs",
        "cobalt_wren.workflows",
    )
    offenders = [module for module in modules if module.startswith(forbidden_prefixes)]
    assert offenders == [], f"{path} imports forbidden modules: {offenders}"


def test_runtime_artifact_store_builder_uses_config_and_integrations_only() -> None:
    path = Path("src/cobalt_wren/runtime/artifact_store.py")
    modules = _imported_modules(path)

    assert any(module.startswith("cobalt_wren.config.artifact_store") for module in modules)
    assert any(module.startswith("cobalt_wren.integrations.artifact") for module in modules)
