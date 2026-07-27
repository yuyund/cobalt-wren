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
        "cobalt_wren.api.plugins",
        "cobalt_wren.plugins.registry",
        "cobalt_wren.apps.automation",
        "cobalt_wren.graphs.runner",
        "cobalt_wren.graphs.builders",
        "cobalt_wren.workflows.catalog",
        "cobalt_wren.integrations.",
        "django",
    )

    for relative in (
        Path("src/cobalt_wren/config/__init__.py"),
        Path("src/cobalt_wren/config/artifact_store.py"),
        Path("src/cobalt_wren/config/loader.py"),
        Path("src/cobalt_wren/config/models.py"),
        Path("src/cobalt_wren/config/normalizer.py"),
        Path("src/cobalt_wren/config/security.py"),
    ):
        modules = _imported_modules(relative)
        offenders = [module for module in modules if module.startswith(forbidden_prefixes)]
        assert offenders == [], f"{relative} imports forbidden modules: {offenders}"
