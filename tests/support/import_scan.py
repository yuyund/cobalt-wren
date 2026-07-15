"""Import scanning helpers for architecture boundary tests."""

from __future__ import annotations

import ast
from pathlib import Path


def collect_import_targets(path: Path) -> list[str]:
    """Return normalized import targets found in a Python module."""
    tree = ast.parse(path.read_text())
    targets: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            targets.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            targets.append(node.module)
            targets.extend(f"{node.module}.{alias.name}" for alias in node.names if alias.name != "*")
    return targets
