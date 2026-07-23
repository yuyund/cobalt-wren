"""Separate distribution installation and entry-point execution proof."""

from __future__ import annotations
import json
from pathlib import Path
import os
import site
import subprocess
import sys


def test_separate_distribution_installs_and_executes_via_entry_point(
    tmp_path: Path,
) -> None:
    repo = Path(__file__).resolve().parents[3]
    external = repo / "tests" / "external_distributions" / "acme_workflows"
    venv = tmp_path / "venv"
    subprocess.run(
        [sys.executable, "-m", "venv", "--system-site-packages", str(venv)], check=True
    )
    python = venv / "bin" / "python"
    for package in (repo, external):
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
from langgraph_automation.api.engine import create_engine
distributions = {dist.metadata["Name"] for dist in metadata.distributions()}
entries = metadata.entry_points().select(group="langgraph_automation.plugins")
prepared = create_engine({"version": 1, "environment": "test"}, discover_plugins=True).prepare_workflow("acme.installed_review", config={"prefix": "wheel"})
result = prepared.execute({"request_id": "REQ-9"})
print(json.dumps({"foundation_installed": "langgraph-automation" in distributions, "external_installed": "acme-workflows" in distributions, "entry_points": sorted(entry.name for entry in entries), "output": dict(result.output)}))
"""
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(site.getsitepackages())
    completed = subprocess.run(
        [str(python), "-c", script],
        check=True,
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env=env,
    )
    payload = json.loads(completed.stdout.strip())
    assert payload["foundation_installed"] is True
    assert payload["external_installed"] is True
    assert "acme" in payload["entry_points"]
    assert payload["output"] == {"message": "wheel:REQ-9"}
