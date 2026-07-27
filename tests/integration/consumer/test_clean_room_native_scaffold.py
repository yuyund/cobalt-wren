from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


def test_native_scaffold_builds_loads_and_executes_from_wheels(tmp_path: Path) -> None:
    repo = Path(__file__).parents[3]
    generated = tmp_path / "generated"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "cobalt_wren",
            "init-workflow",
            "--name",
            "native-consumer",
            "--kind",
            "consumer.native",
            "--framework",
            "native",
            "--output",
            str(generated),
        ],
        cwd=repo,
        check=True,
        env={**os.environ, "PYTHONPATH": str(repo / "src")},
    )
    package = generated / "native-consumer"
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()
    subprocess.run(
        [sys.executable, "-m", "pip", "wheel", "--wheel-dir", str(wheelhouse), str(repo), str(package)],
        check=True,
        capture_output=True,
        text=True,
    )
    venv = tmp_path / "venv"
    subprocess.run([sys.executable, "-m", "venv", "--system-site-packages", str(venv)], check=True)
    python = venv / "bin" / "python"
    for wheel in sorted(wheelhouse.glob("*.whl")):
        subprocess.run(
            [str(python), "-m", "pip", "install", "--no-deps", str(wheel)],
            check=True,
            capture_output=True,
            text=True,
        )
    code = """
from importlib import metadata
from cobalt_wren.api.engine import create_engine
from cobalt_wren.api.workflow import WorkflowExecutionContext
entry = next(x for x in metadata.entry_points().select(group='cobalt_wren.plugins') if x.name == 'native-consumer')
plugin = entry.load()()
engine = create_engine({'version': 1}, discover_plugins=True)
prepared = engine.prepare_workflow('consumer.native')
result = prepared.execute({'message': ' clean-room '}, context=WorkflowExecutionContext(run_id=501))
print(result.output['message'])
print(result.metadata['integration_id'])
print(prepared.input_schema['properties']['message']['type'])
"""
    completed = subprocess.run(
        [str(python), "-c", code],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    assert completed.stdout.splitlines() == ["clean-room", "native", "string"]
