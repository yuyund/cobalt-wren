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
    path = Path("src/cobalt_wren/api/engine.py")
    modules = _imported_modules(path)

    forbidden_prefixes = (
        "cobalt_wren.apps.automation",
        "django",
        "django.conf",
        "django.db",
        "cobalt_wren.graphs.runner",
        "cobalt_wren.graphs.builders",
    )
    offenders = [module for module in modules if module.startswith(forbidden_prefixes)]
    assert offenders == [], f"{path} imports forbidden modules: {offenders}"

    for expected in (
        "cobalt_wren.api.errors",
        "cobalt_wren.api.plugins",
        "cobalt_wren.config.loader",
        "cobalt_wren.config.models",
        "cobalt_wren.config.normalizer",
        "cobalt_wren.config.validator",
        "cobalt_wren.runtime.assembly",
        "cobalt_wren.runtime.dependencies",
        "cobalt_wren.runtime.secrets",
        "cobalt_wren.workflows.catalog",
        "cobalt_wren.workflows.prepare",
    ):
        assert expected in modules


def test_api_runtime_facade_is_not_created_yet() -> None:
    assert not Path("src/cobalt_wren/api/runtime.py").exists()
