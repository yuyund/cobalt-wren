"""Runtime assembler boundary tests."""

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


def test_runtime_package_does_not_import_forbidden_boundaries() -> None:
    forbidden_prefixes = (
        'cobalt_wren.plugins.registry',
        'cobalt_wren.apps.automation',
        'cobalt_wren.graphs.runner',
        'cobalt_wren.graphs.builders',
        'cobalt_wren.workflows.catalog',
        'cobalt_wren.integrations.',
        'django',
    )
    allowed_imports = {
        'cobalt_wren.integrations.checkpoint.base',
    }

    for relative in (
        Path('src/cobalt_wren/runtime/__init__.py'),
        Path('src/cobalt_wren/runtime/dependencies.py'),
        Path('src/cobalt_wren/runtime/context.py'),
        Path('src/cobalt_wren/runtime/secrets.py'),
        Path('src/cobalt_wren/runtime/assembly.py'),
    ):
        modules = _imported_modules(relative)
        offenders = [module for module in modules if module.startswith(forbidden_prefixes) and module not in allowed_imports]
        assert offenders == [], f'{relative} imports forbidden modules: {offenders}'


def test_runtime_package_may_import_public_facades_only() -> None:
    modules = []
    for relative in (
        Path('src/cobalt_wren/runtime/context.py'),
        Path('src/cobalt_wren/runtime/secrets.py'),
        Path('src/cobalt_wren/runtime/assembly.py'),
    ):
        modules.extend(_imported_modules(relative))

    assert any(module.startswith('cobalt_wren.api.errors') for module in modules)
    assert any(module.startswith('cobalt_wren.config.models') for module in modules)
