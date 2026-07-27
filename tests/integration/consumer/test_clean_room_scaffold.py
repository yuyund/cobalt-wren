from __future__ import annotations

from pathlib import Path
import os
import subprocess
import sys


def test_scaffolded_consumer_builds_and_loads_from_wheels(tmp_path: Path) -> None:
    repo = Path(__file__).parents[3]
    generated = tmp_path / "generated"
    subprocess.run([sys.executable, "-m", "cobalt_wren", "init-workflow", "--name", "consumer-workflow", "--kind", "consumer.echo", "--output", str(generated)], cwd=repo, check=True, env={**os.environ, "PYTHONPATH": str(repo / "src")})
    package = generated / "consumer-workflow"
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()
    subprocess.run([sys.executable, "-m", "pip", "wheel", "--wheel-dir", str(wheelhouse), str(repo), str(package)], check=True, capture_output=True, text=True)
    venv = tmp_path / "venv"
    subprocess.run([sys.executable, "-m", "venv", "--system-site-packages", str(venv)], check=True)
    python = venv / "bin" / "python"
    for wheel in sorted(wheelhouse.glob("*.whl")):
        subprocess.run([str(python), "-m", "pip", "install", "--no-deps", str(wheel)], check=True, capture_output=True, text=True)
    code = """
from importlib import metadata
from cobalt_wren.api.engine import create_engine
from cobalt_wren.api.workflow import WorkflowExecutionContext
entry = next(x for x in metadata.entry_points().select(group='cobalt_wren.plugins') if x.name == 'consumer-workflow')
plugin = entry.load()()
engine = create_engine({'version': 1}, discover_plugins=True)
result = engine.prepare_workflow('consumer.echo').execute({'message': 'clean-room'}, context=WorkflowExecutionContext(thread_id='consumer'))
print(result.output['message'])
"""
    completed = subprocess.run([str(python), "-c", code], cwd=tmp_path, check=True, capture_output=True, text=True)
    assert completed.stdout.strip() == "clean-room"
