from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).parents[3]
SRC = ROOT / "packages" / "plain_python_workflow" / "src"
sys.path.insert(0, str(SRC))

from plain_python_workflow import WORKFLOW_KIND, create_plugin  # noqa: E402
from cobalt_wren.api.engine import create_engine  # noqa: E402
from cobalt_wren.api.workflow import WorkflowExecutionContext, WorkflowResumeRequest  # noqa: E402


def test_plain_python_distribution_pauses_and_resumes_without_langgraph(tmp_path: Path) -> None:
    engine = create_engine(
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
    context = WorkflowExecutionContext(run_id=700, thread_id="plain-700")
    first = engine.prepare_workflow(WORKFLOW_KIND).execute(
        {"subject": "Framework boundary", "message": "Confirm without LangGraph"},
        context=context,
    )
    assert first.status == "paused"
    assert first.metadata["framework"] == "none"
    resumed = engine.prepare_workflow(WORKFLOW_KIND).resume(
        WorkflowResumeRequest(value={"action": "confirm", "note": "Verified"}),
        context=context,
    )
    assert resumed.output["decision"] == "confirmed"
    assert resumed.output["artifact_key"] == "plain-confirmation/700/decision.json"
