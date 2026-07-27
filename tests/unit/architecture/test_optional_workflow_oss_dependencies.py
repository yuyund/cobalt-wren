"""Architecture guards for optional workflow OSS dependencies."""

from __future__ import annotations

import ast
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[3]


def test_framework_distributions_are_owned_by_consuming_packages() -> None:
    import tomllib

    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project_dependencies = data["project"]["dependencies"]
    optional_dependencies = data["project"]["optional-dependencies"]

    assert not any(item.startswith("langgraph") for item in project_dependencies)
    assert not any(item.startswith("llama-index-workflows") for item in project_dependencies)
    assert "langgraph" not in optional_dependencies
    assert "llamaindex" not in optional_dependencies
    assert "oss-integrations" not in optional_dependencies
    assert any(item.startswith("langgraph") for item in optional_dependencies["dev"])
    assert any(item.startswith("llama-index-workflows") for item in optional_dependencies["dev"])


def test_foundation_and_native_reference_import_without_langgraph() -> None:
    script = r'''
import importlib.abc
import sys

class BlockLangGraph(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "langgraph" or fullname.startswith("langgraph."):
            raise ModuleNotFoundError("langgraph intentionally unavailable")
        return None

sys.meta_path.insert(0, BlockLangGraph())

from cobalt_wren.api.engine import create_engine
from cobalt_wren.native import NativeWorkflow
from cobalt_wren.workflows.catalog import create_builtin_workflow_registry

registry = create_builtin_workflow_registry()
assert registry.list_plugins() == ()
engine = create_engine({"version": 1}, discover_plugins=False)
assert engine is not None
'''
    subprocess.run(
        [sys.executable, "-c", script],
        check=True,
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def test_native_example_has_no_workflow_oss_import() -> None:
    path = (
        ROOT
        / "examples"
        / "native"
        / "sequential_pipeline.py"
    )
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imports.append(node.module)

    assert "cobalt_wren.native" in imports
    assert not any(
        module == "langgraph" or module.startswith("langgraph.")
        for module in imports
    )
    assert not any(
        module == "workflows" or module.startswith("workflows.")
        for module in imports
    )
