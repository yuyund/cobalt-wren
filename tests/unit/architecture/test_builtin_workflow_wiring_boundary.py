"""Architecture guard for built-in workflow wiring boundaries."""

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


def test_workflow_catalog_uses_registry_boundary_only() -> None:
    modules = _imported_modules(Path("src/cobalt_wren/workflows/catalog.py"))

    assert "cobalt_wren.api.plugins" in modules
    assert "cobalt_wren.plugins.registry" in modules
    assert "cobalt_wren.workflows.adapter" not in modules
    assert not any("reference" in module for module in modules)
    assert not any("examples" in module for module in modules)
    assert not any(module.startswith("cobalt_wren.native") for module in modules)
    assert not any(module.startswith("cobalt_wren.graphs") for module in modules)

    offenders = [
        module
        for module in modules
        if module.startswith(
            (
                "cobalt_wren.runtime",
                "cobalt_wren.config.validator",
                "cobalt_wren.apps.automation",
                "django",
            )
        )
    ]
    assert offenders == []


def test_workflow_adapter_stays_inside_workflow_and_error_facades() -> None:
    modules = _imported_modules(Path('src/cobalt_wren/workflows/adapter.py'))

    assert 'cobalt_wren.api.errors' in modules
    assert 'cobalt_wren.api.workflow' in modules
    offenders = [module for module in modules if module.startswith('cobalt_wren.runtime')]
    assert offenders == []


def test_workflow_requirements_checker_depends_on_runtime_dependencies_only() -> None:
    modules = _imported_modules(Path('src/cobalt_wren/workflows/requirements.py'))

    assert 'cobalt_wren.api.errors' in modules
    assert 'cobalt_wren.api.workflow' in modules
    assert 'cobalt_wren.runtime.dependencies' in modules
    offenders = [module for module in modules if module.startswith('cobalt_wren.apps.automation')]
    assert offenders == []
