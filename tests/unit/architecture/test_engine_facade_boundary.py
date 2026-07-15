"""Architecture guard for the package engine facade."""

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


def test_api_engine_imports_only_allowed_package_facades_and_internal_layers() -> None:
    path = Path("src/langgraph_automation/api/engine.py")
    modules = _imported_modules(path)

    forbidden_prefixes = (
        "langgraph_automation.apps.automation",
        "django",
        "django.conf",
        "django.db",
        "langgraph_automation.workflows.reference",
        "langgraph_automation.graphs.runner",
        "langgraph_automation.graphs.builders",
    )
    offenders = [module for module in modules if module.startswith(forbidden_prefixes)]
    assert offenders == [], f"{path} imports forbidden modules: {offenders}"

    for expected in (
        "langgraph_automation.api.errors",
        "langgraph_automation.api.plugins",
        "langgraph_automation.config.loader",
        "langgraph_automation.config.models",
        "langgraph_automation.config.normalizer",
        "langgraph_automation.config.validator",
        "langgraph_automation.runtime.assembly",
        "langgraph_automation.runtime.dependencies",
        "langgraph_automation.runtime.secrets",
        "langgraph_automation.workflows.catalog",
        "langgraph_automation.workflows.prepare",
    ):
        assert expected in modules


def test_api_runtime_facade_is_not_created_yet() -> None:
    assert not Path("src/langgraph_automation/api/runtime.py").exists()
