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
    path = Path("src/langgraph_automation/runtime/artifact_store.py")
    modules = _imported_modules(path)

    forbidden_prefixes = (
        "django",
        "langgraph_automation.apps.automation",
        "langgraph_automation.graphs",
        "langgraph_automation.workflows",
    )
    offenders = [module for module in modules if module.startswith(forbidden_prefixes)]
    assert offenders == [], f"{path} imports forbidden modules: {offenders}"


def test_runtime_artifact_store_builder_uses_config_and_integrations_only() -> None:
    path = Path("src/langgraph_automation/runtime/artifact_store.py")
    modules = _imported_modules(path)

    assert any(module.startswith("langgraph_automation.config.artifact_store") for module in modules)
    assert any(module.startswith("langgraph_automation.integrations.artifact") for module in modules)
