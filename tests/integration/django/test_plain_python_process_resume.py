from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


def test_plain_python_resume_crosses_a_real_process_boundary(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[3]
    database = tmp_path / "control-plane.sqlite3"
    artifacts = tmp_path / "artifacts"
    checkpoints = tmp_path / "checkpoints"
    env = dict(os.environ)
    env.update({
        "DATABASE_URL": f"sqlite:///{database}",
        "DJANGO_SETTINGS_MODULE": "langgraph_automation.config.settings",
        "PYTHONPATH": os.pathsep.join([str(repo / "src"), str(repo / "packages" / "plain_python_workflow" / "src")]),
        "PLAIN_ARTIFACT_ROOT": str(artifacts),
        "PLAIN_CHECKPOINT_ROOT": str(checkpoints),
    })
    common = """
import os, django
django.setup()
from plain_python_workflow import WORKFLOW_KIND, create_plugin
from langgraph_automation.apps.automation.services.runtime import build_run_execution_services
services = build_run_execution_services({'version': 1, 'stores': {'artifact': {'backend': 'filesystem', 'config': {'root': os.environ['PLAIN_ARTIFACT_ROOT']}}, 'checkpoint': {'backend': 'filesystem', 'config': {'root': os.environ['PLAIN_CHECKPOINT_ROOT']}}}}, plugins=(create_plugin(),), discover_plugins=False)
"""
    process_a = common + """
from django.core.management import call_command
from langgraph_automation.apps.automation.models import Workflow, Run
from langgraph_automation.apps.automation.services.runs import start_run
call_command('migrate', interactive=False, verbosity=0)
workflow = Workflow.objects.create(name='cross-process-plain', definition_payload={'workflow': {'kind': WORKFLOW_KIND, 'config': {}}})
run = Run.objects.create(workflow=workflow, name='cross-process-run', input_payload={'subject': 'Process boundary', 'message': 'Resume from another interpreter'})
result = start_run(run=run, services=services)
print(result.run.pk)
"""
    started = subprocess.run([sys.executable, "-c", process_a], check=True, capture_output=True, text=True, env=env, cwd=tmp_path)
    run_id = int(started.stdout.strip().splitlines()[-1])

    process_b = common + f"""
import json
from langgraph_automation.apps.automation.models import Run
from langgraph_automation.apps.automation.services.runs import resume_run
run = Run.objects.get(pk={run_id})
result = resume_run(run=run, resume_payload={{'action': 'confirm', 'note': 'Second process'}}, services=services)
result.run.refresh_from_db()
print(json.dumps({{'status': result.run.status, 'artifact_count': result.run.artifacts.count(), 'checkpoint_count': result.run.checkpoint_metadata.count(), 'thread_id': result.run.thread_id}}))
"""
    resumed = subprocess.run([sys.executable, "-c", process_b], check=True, capture_output=True, text=True, env=env, cwd=tmp_path)
    payload = json.loads(resumed.stdout.strip().splitlines()[-1])
    assert payload == {"status": "succeeded", "artifact_count": 1, "checkpoint_count": 2, "thread_id": f"run-{run_id}"}
