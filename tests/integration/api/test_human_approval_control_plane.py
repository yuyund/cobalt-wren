from __future__ import annotations

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).parents[3]
PACKAGE_SRC = ROOT / "packages" / "human_approval_workflow" / "src"
sys.path.insert(0, str(PACKAGE_SRC))

from human_approval_workflow import WORKFLOW_KIND, create_plugin  # noqa: E402
from langgraph_automation.apps.automation.models.run import Run, RunStatus  # noqa: E402
from langgraph_automation.apps.automation.models.workflow import Workflow  # noqa: E402
from langgraph_automation.apps.automation.services import runs as run_services  # noqa: E402
from langgraph_automation.apps.automation.services import runtime as runtime_module  # noqa: E402


@pytest.mark.django_db
def test_control_plane_pauses_reprepares_and_resumes_to_success(tmp_path: Path) -> None:
    services = runtime_module.build_run_execution_services(
        {
            "version": 1,
            "stores": {
                "artifact": {"backend": "filesystem", "config": {"root": str(tmp_path / "artifacts")}},
                "checkpoint": {"backend": "filesystem", "config": {"root": str(tmp_path / "checkpoints")}},
            },
        },
        plugins=(create_plugin(),),
        discover_plugins=False,
    )
    workflow = Workflow.objects.create(
        name="human-approval",
        definition_payload={"workflow": {"kind": WORKFLOW_KIND, "config": {}}},
    )
    run = Run.objects.create(
        workflow=workflow,
        name="approval-run",
        input_payload={"title": "Release", "proposal": "Deploy version 1"},
    )

    started = run_services.start_run(run=run, services=services)
    assert started.run.status == RunStatus.WAITING
    assert started.execution_result is not None
    checkpoint_id = started.execution_result.output_payload["checkpoint_id"]

    resumed = run_services.resume_run(
        run=started.run,
        resume_payload={"decision": "approve", "note": "Validated"},
        checkpoint_id=str(checkpoint_id),
        services=services,
    )
    resumed.run.refresh_from_db()
    assert resumed.run.status == RunStatus.SUCCEEDED
    assert resumed.execution_result is not None
    assert resumed.execution_result.output_payload["decision"] == "approved"
    assert resumed.execution_result.output_payload["artifact_key"].endswith("/decision.json")

    with pytest.raises(PermissionError):
        run_services.resume_run(
            run=resumed.run,
            resume_payload={"decision": "approve"},
            services=services,
        )
