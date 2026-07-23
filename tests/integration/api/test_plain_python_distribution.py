from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile


def test_plain_python_installs_without_langgraph_dependency(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[3]
    external = repo / "packages" / "plain_python_workflow"
    wheelhouse = tmp_path / "wheels"
    venv = tmp_path / "venv"
    wheelhouse.mkdir()
    subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
    subprocess.run([sys.executable, "-m", "pip", "wheel", "--wheel-dir", str(wheelhouse), str(repo), str(external)], check=True, capture_output=True, text=True)
    external_wheel = next(wheelhouse.glob("plain_python_workflow-*.whl"))
    with zipfile.ZipFile(external_wheel) as archive:
        metadata_name = next(name for name in archive.namelist() if name.endswith(".dist-info/METADATA"))
        metadata_text = archive.read(metadata_name).decode()
    requirements = [line.removeprefix("Requires-Dist: ") for line in metadata_text.splitlines() if line.startswith("Requires-Dist: ")]
    assert any(item.startswith("langgraph-automation") for item in requirements)
    assert not any(item == "langgraph" or item.startswith("langgraph ") for item in requirements)

    python = venv / "bin" / "python"
    for wheel in sorted(wheelhouse.glob("*.whl")):
        subprocess.run([str(python), "-m", "pip", "install", "--no-deps", str(wheel)], check=True, capture_output=True, text=True)
    code = """
import json
from importlib import metadata
entry = next(x for x in metadata.entry_points().select(group='langgraph_automation.plugins') if x.name == 'plain-python')
plugin = entry.load()()
workflow = plugin.contributions.workflows[0]
print(json.dumps({'entry': entry.name, 'kind': workflow.kind, 'framework': workflow.definition.metadata.metadata['framework']}))
"""
    completed = subprocess.run([str(python), "-c", code], check=True, capture_output=True, text=True, cwd=tmp_path, env=dict(os.environ))
    assert json.loads(completed.stdout) == {"entry": "plain-python", "kind": "plain.confirmation", "framework": "none"}
