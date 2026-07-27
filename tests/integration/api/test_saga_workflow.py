from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).parents[3]
SRC = ROOT / "packages" / "saga_workflow" / "src"
sys.path.insert(0, str(SRC))

from saga_workflow import WORKFLOW_KIND, create_plugin  # noqa: E402
from cobalt_wren.api.engine import create_engine  # noqa: E402
from cobalt_wren.api.workflow import WorkflowExecutionContext, WorkflowResumeRequest  # noqa: E402


def _engine(tmp_path: Path):
    return create_engine({"version": 1, "stores": {"artifact": {"backend": "filesystem", "config": {"root": str(tmp_path / "artifacts")}}, "checkpoint": {"backend": "filesystem", "config": {"root": str(tmp_path / "checkpoints")}}}}, plugins=(create_plugin(),), discover_plugins=False)


def test_all_parallel_branches_succeed(tmp_path: Path) -> None:
    result = _engine(tmp_path).prepare_workflow(WORKFLOW_KIND).execute({"order_id": "ORD-1"}, context=WorkflowExecutionContext(run_id=1, thread_id="saga-1"))
    assert result.status == "completed"
    assert result.output["status"] == "completed"
    assert {item["operation"] for item in result.output["results"]} == {"reserve_inventory", "charge_payment", "provision_access"}
    assert all(item["status"] == "succeeded" for item in result.output["results"])


def test_retryable_partial_failure_resumes_only_failed_branch(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    context = WorkflowExecutionContext(run_id=2, thread_id="saga-2")
    first = engine.prepare_workflow(WORKFLOW_KIND).execute({"order_id": "ORD-2", "failure_plan": {"charge_payment": "retryable"}}, context=context)
    assert first.status == "paused"
    assert first.output["allowed_actions"] == ["retry_failed", "compensate"]
    assert len([item for item in first.output["results"] if item["status"] == "failed"]) == 1
    resumed = engine.prepare_workflow(WORKFLOW_KIND).resume(WorkflowResumeRequest(value={"action": "retry_failed"}), context=context)
    assert resumed.output["status"] == "completed"
    payment = next(item for item in resumed.output["results"] if item["operation"] == "charge_payment")
    assert payment["attempt"] == 2
    assert len(resumed.output["results"]) == 3


def test_fatal_failure_compensates_successes_in_reverse_order(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    context = WorkflowExecutionContext(run_id=3, thread_id="saga-3")
    first = engine.prepare_workflow(WORKFLOW_KIND).execute({"order_id": "ORD-3", "failure_plan": {"provision_access": "fatal"}}, context=context)
    assert first.status == "paused"
    assert first.output["allowed_actions"] == ["compensate"]
    resumed = engine.prepare_workflow(WORKFLOW_KIND).resume(WorkflowResumeRequest(value={"action": "compensate"}), context=context)
    assert resumed.output["status"] == "compensated"
    assert [item["operation"] for item in resumed.output["compensations"]] == ["refund_payment", "release_inventory"]
    assert len({item["idempotency_key"] for item in resumed.output["compensations"]}) == 2
