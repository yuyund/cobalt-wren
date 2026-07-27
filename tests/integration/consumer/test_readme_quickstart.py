from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


def _run(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "cobalt_wren", *args],
        cwd=repo,
        env={**os.environ, "PYTHONPATH": str(repo / "src")},
        check=True,
        capture_output=True,
        text=True,
    )


def test_readme_quickstart_is_executable() -> None:
    repo = Path(__file__).parents[3]
    target = "examples.quickstart.workflow:greeting"

    inspected = json.loads(_run(repo, "native-inspect", target).stdout)
    validated = json.loads(_run(repo, "native-validate", target).stdout)
    executed = json.loads(
        _run(repo, "native-run", target, "--input", '{"name":"README"}').stdout
    )

    assert inspected["workflow"] == "example.greeting"
    assert validated["status"] == "valid"
    assert executed["output"] == {"message": "Hello, README."}
