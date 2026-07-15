"""Architecture guard for config core boundaries."""

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


def test_config_core_modules_do_not_import_forbidden_boundaries() -> None:
    forbidden_prefixes = (
        "langgraph_automation.api.plugins",
        "langgraph_automation.plugins.registry",
        "langgraph_automation.apps.automation",
        "langgraph_automation.graphs.runner",
        "langgraph_automation.graphs.builders",
        "langgraph_automation.workflows.catalog",
        "langgraph_automation.integrations.",
        "django",
    )

    for relative in (
        Path("src/langgraph_automation/config/__init__.py"),
        Path("src/langgraph_automation/config/loader.py"),
        Path("src/langgraph_automation/config/models.py"),
        Path("src/langgraph_automation/config/normalizer.py"),
        Path("src/langgraph_automation/config/security.py"),
    ):
        modules = _imported_modules(relative)
        offenders = [module for module in modules if module.startswith(forbidden_prefixes)]
        assert offenders == [], f"{relative} imports forbidden modules: {offenders}"
