from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


def test_human_approval_installs_as_separate_distribution(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[3]
    external = repo / "packages" / "human_approval_workflow"
    venv = tmp_path / "venv"
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()
    subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
    subprocess.run(
        [sys.executable, "-m", "pip", "wheel", "--wheel-dir", str(wheelhouse), str(repo), str(external)],
        check=True,
        capture_output=True,
        text=True,
    )
    python = venv / "bin" / "python"
    for wheel in sorted(wheelhouse.glob("*.whl")):
        subprocess.run([str(python), "-m", "pip", "install", "--no-deps", str(wheel)], check=True, capture_output=True, text=True)
    script = """
import json
from importlib import metadata
from human_approval_workflow import WORKFLOW_KIND
entry = next(item for item in metadata.entry_points().select(group='cobalt_wren.plugins') if item.name == 'human-approval')
plugin = entry.load()()
workflow = next(item for item in plugin.contributions.workflows if item.kind == WORKFLOW_KIND)
print(json.dumps({'entry': entry.name, 'plugin': plugin.metadata.name, 'workflow': workflow.kind, 'capabilities': workflow.definition.extra['capabilities']}))
"""
    completed = subprocess.run([str(python), "-c", script], check=True, capture_output=True, text=True, cwd=tmp_path, env=dict(os.environ))
    assert json.loads(completed.stdout) == {
        "entry": "human-approval",
        "plugin": "human-approval-workflow",
        "workflow": "human.approval",
        "capabilities": ["pause", "resume", "human-input", "revision-loop"],
    }
