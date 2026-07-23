from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess
import sys


def test_saga_installs_as_separate_distribution(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[3]
    external = repo / "packages" / "saga_workflow"
    venv = tmp_path / "venv"
    wheels = tmp_path / "wheels"
    wheels.mkdir()
    subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
    subprocess.run([sys.executable, "-m", "pip", "wheel", "--wheel-dir", str(wheels), str(repo), str(external)], check=True, capture_output=True, text=True)
    python = venv / "bin" / "python"
    for wheel in sorted(wheels.glob("*.whl")):
        subprocess.run([str(python), "-m", "pip", "install", "--no-deps", str(wheel)], check=True, capture_output=True, text=True)
    code = """
import json
from importlib import metadata
entry = next(x for x in metadata.entry_points().select(group='langgraph_automation.plugins') if x.name == 'saga')
plugin = entry.load()()
w = plugin.contributions.workflows[0]
print(json.dumps({'entry': entry.name, 'kind': w.kind, 'capabilities': w.definition.extra['capabilities']}))
"""
    completed = subprocess.run([str(python), "-c", code], check=True, capture_output=True, text=True, cwd=tmp_path, env=dict(os.environ))
    assert json.loads(completed.stdout)["kind"] == "saga.order_fulfillment"
