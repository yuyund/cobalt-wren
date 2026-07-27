from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


def test_opportunity_workflow_installs_as_separate_distribution(
    tmp_path: Path,
) -> None:
    repo = Path(__file__).resolve().parents[3]
    external = repo / "packages" / "opportunity_research_workflow"
    venv = tmp_path / "venv"
    subprocess.run(
        [sys.executable, "-m", "venv", str(venv)],
        check=True,
    )
    python = venv / "bin" / "python"
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()
    subprocess.run([sys.executable, "-m", "pip", "wheel", "--wheel-dir", str(wheelhouse), str(repo), str(external)], check=True, capture_output=True, text=True)
    for package in sorted(wheelhouse.glob("*.whl")):
        subprocess.run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--no-build-isolation",
                "--no-deps",
                str(package),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    script = """
import json
from importlib import metadata
from opportunity_research_workflow import WORKFLOW_KIND
entries = metadata.entry_points().select(group='cobalt_wren.plugins')
entry = next(item for item in entries if item.name == 'opportunity-research')
plugin = entry.load()()
workflow = next(item for item in plugin.contributions.workflows if item.kind == WORKFLOW_KIND)
print(json.dumps({
    'entry_point': entry.name,
    'plugin': plugin.metadata.name,
    'workflow': workflow.kind,
    'research_only': workflow.definition.metadata.metadata['research_only'],
}))
"""
    env = dict(os.environ)
    completed = subprocess.run(
        [str(python), "-c", script],
        check=True,
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env=env,
    )
    assert json.loads(completed.stdout.strip()) == {
        "entry_point": "opportunity-research",
        "plugin": "opportunity-research-workflow",
        "workflow": "opportunity.research",
        "research_only": True,
    }
