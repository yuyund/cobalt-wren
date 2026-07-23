from __future__ import annotations

from pathlib import Path
import sys

import pytest
from django.test import override_settings

ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(ROOT / "packages" / "plain_python_workflow" / "src"))

from plain_python_workflow import create_plugin  # noqa: E402
from langgraph_automation.apps.automation.models import ExecutionJobStatus, Run, RunStatus, Workflow  # noqa: E402
from langgraph_automation.apps.automation.services import runtime as runtime_module  # noqa: E402
from langgraph_automation.apps.automation.services.dispatch import dispatch_start  # noqa: E402
from langgraph_automation.apps.automation.services.jobs import claim_next_job, execute_job  # noqa: E402


@pytest.mark.django_db(transaction=True)
def test_worker_mode_executes_run_outside_dispatch_request(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    services = runtime_module.build_run_execution_services({"version": 1, "stores": {"artifact": {"backend": "filesystem", "config": {"root": str(tmp_path / "artifacts")}}, "checkpoint": {"backend": "filesystem", "config": {"root": str(tmp_path / "checkpoints")}}}}, plugins=(create_plugin(),), discover_plugins=False)
    monkeypatch.setattr(runtime_module, "get_run_execution_services", lambda: services)
    workflow = Workflow.objects.create(name="worker-plain", definition_payload={"workflow": {"kind": "plain.confirmation", "config": {}}})
    run = Run.objects.create(workflow=workflow, name="worker-run", input_payload={"subject": "Worker", "message": "Separate process boundary"})
    with override_settings(LANGGRAPH_AUTOMATION_EXECUTION_MODE="worker"):
        dispatched = dispatch_start(run=run)
    run.refresh_from_db()
    assert run.status == RunStatus.PENDING
    assert dispatched.job is not None
    job = claim_next_job(worker_id="test-worker")
    assert job is not None
    execute_job(job)
    job.refresh_from_db()
    run.refresh_from_db()
    assert job.status == ExecutionJobStatus.SUCCEEDED
    assert run.status == RunStatus.WAITING
