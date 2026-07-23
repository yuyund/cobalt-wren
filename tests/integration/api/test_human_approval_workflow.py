from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).parents[3]
PACKAGE_SRC = ROOT / "packages" / "human_approval_workflow" / "src"
sys.path.insert(0, str(PACKAGE_SRC))

from human_approval_workflow import WORKFLOW_KIND, create_plugin  # noqa: E402
from langgraph_automation.api.engine import create_engine  # noqa: E402
from langgraph_automation.api.workflow import WorkflowExecutionContext, WorkflowResumeRequest  # noqa: E402


def _engine(tmp_path: Path):
    return create_engine(
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


def test_langgraph_approval_pauses_and_resumes_after_reprepare(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    context = WorkflowExecutionContext(run_id=101, thread_id="approval-101")
    first = engine.prepare_workflow(WORKFLOW_KIND).execute(
        {"title": "Publish proposal", "proposal": "Initial proposal"},
        context=context,
    )
    assert first.status == "paused"
    assert first.output["checkpoint_id"] == "approval-pause-0"
    assert first.output["approval_request"]["allowed_decisions"] == ["approve", "reject", "revise"]

    resumed = engine.prepare_workflow(WORKFLOW_KIND).resume(
        WorkflowResumeRequest(value={"decision": "approve", "note": "Reviewed"}),
        context=context,
    )
    assert resumed.status == "completed"
    assert resumed.output["decision"] == "approved"
    assert resumed.output["artifact_key"] == "human-approval/101/decision.json"


def test_revision_loops_back_to_a_second_pause_then_can_be_rejected(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    context = WorkflowExecutionContext(run_id=202, thread_id="approval-202")
    engine.prepare_workflow(WORKFLOW_KIND).execute(
        {"title": "Contract", "proposal": "Version one"},
        context=context,
    )
    revised = engine.prepare_workflow(WORKFLOW_KIND).resume(
        WorkflowResumeRequest(value={"decision": "revise", "proposal": "Version two"}),
        context=context,
    )
    assert revised.status == "paused"
    assert revised.output["approval_request"]["proposal"] == "Version two"
    assert revised.output["approval_request"]["revision_count"] == 1

    rejected = engine.prepare_workflow(WORKFLOW_KIND).resume(
        WorkflowResumeRequest(value={"decision": "reject", "note": "Not viable"}),
        context=context,
    )
    assert rejected.output["decision"] == "rejected"
    assert rejected.output["proposal"] == "Version two"
    assert rejected.output["revision_count"] == 1


def test_plain_python_resumable_uses_same_public_contract() -> None:
    from langgraph_automation.workflows.adapter import execute_workflow, resume_workflow

    class PlainPythonWorkflow:
        def execute(self, input_payload, *, context):
            return {"paused": True}

        def resume(self, request, *, context):
            return {"decision": request.value["decision"]}

    workflow = PlainPythonWorkflow()
    assert execute_workflow(workflow, {}).output == {"paused": True}
    assert resume_workflow(workflow, WorkflowResumeRequest(value={"decision": "approve"})).output == {"decision": "approve"}
