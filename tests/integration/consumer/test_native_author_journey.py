from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


def test_native_author_journey_from_scaffold_to_validation_and_local_run(tmp_path: Path) -> None:
    repo = Path(__file__).parents[3]
    generated = tmp_path / "generated"
    environment = {**os.environ, "PYTHONPATH": str(repo / "src")}
    subprocess.run(
        [sys.executable, "-m", "cobalt_wren", "init-workflow", "--name", "journey-native", "--kind", "journey.native", "--framework", "native", "--output", str(generated)],
        cwd=repo, check=True, env=environment, capture_output=True, text=True,
    )
    package_src = generated / "journey-native" / "src"
    journey_env = {**environment, "PYTHONPATH": os.pathsep.join([str(repo / "src"), str(package_src)])}
    valid = subprocess.run(
        [sys.executable, "-m", "cobalt_wren", "native-validate", "journey_native.workflow:WORKFLOW", "--input", '{"message":" hello "}'],
        cwd=repo, env=journey_env, capture_output=True, text=True, check=True,
    )
    assert json.loads(valid.stdout)["status"] == "valid"
    invalid = subprocess.run(
        [sys.executable, "-m", "cobalt_wren", "native-validate", "journey_native.workflow:WORKFLOW", "--input", '{}'],
        cwd=repo, env=journey_env, capture_output=True, text=True,
    )
    assert invalid.returncode == 1
    assert json.loads(invalid.stdout)["issues"] == ["$.message: field is required"]
    executed = subprocess.run(
        [sys.executable, "-m", "cobalt_wren", "native-run", "journey_native.workflow:WORKFLOW", "--input", '{"message":" hello "}'],
        cwd=repo, env=journey_env, capture_output=True, text=True, check=True,
    )
    result = json.loads(executed.stdout)
    assert result["status"] == "completed"
    assert result["output"] == {"message": "hello"}
    assert result["metadata"]["last_step_name"] == "format-message"
