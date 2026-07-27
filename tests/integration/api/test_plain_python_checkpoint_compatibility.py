from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).parents[3]
SRC = ROOT / "packages" / "plain_python_workflow" / "src"
sys.path.insert(0, str(SRC))

from plain_python_workflow import WORKFLOW_KIND, create_plugin  # noqa: E402
from cobalt_wren.api.engine import create_engine  # noqa: E402
from cobalt_wren.api.errors import WorkflowCheckpointCompatibilityError  # noqa: E402
from cobalt_wren.api.stores import CheckpointWriteRequest  # noqa: E402
from cobalt_wren.api.workflow import WorkflowExecutionContext, WorkflowResumeRequest  # noqa: E402


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


def test_legacy_v0_checkpoint_is_migrated_before_resume(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    executable = engine.prepare_workflow(WORKFLOW_KIND)
    context = WorkflowExecutionContext(run_id=801, thread_id="plain-801")
    store = executable.executable.checkpoint_store
    store.save(
        CheckpointWriteRequest(
            run_id=801,
            checkpoint_id="legacy-v0",
            body=json.dumps({"title": "Legacy subject", "body": "Legacy message", "phase": "awaiting_confirmation"}).encode(),
            serializer_name="json",
            serializer_version=1,
            content_type="application/json",
            checkpoint_namespace="plain-confirmation",
            metadata={"schema_version": 0},
        )
    )
    result = executable.resume(
        WorkflowResumeRequest(value={"action": "confirm"}, checkpoint_id="legacy-v0"),
        context=context,
    )
    assert result.output["decision"] == "confirmed"
    assert result.output["subject"] == "Legacy subject"


def test_unknown_checkpoint_version_is_explicitly_incompatible(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    executable = engine.prepare_workflow(WORKFLOW_KIND)
    context = WorkflowExecutionContext(run_id=802, thread_id="plain-802")
    store = executable.executable.checkpoint_store
    store.save(
        CheckpointWriteRequest(
            run_id=802,
            checkpoint_id="future-v99",
            body=json.dumps({"schema_version": 99, "phase": "awaiting_confirmation"}).encode(),
            serializer_name="json",
            serializer_version=1,
            content_type="application/json",
            checkpoint_namespace="plain-confirmation",
            metadata={"schema_version": 99},
        )
    )
    with pytest.raises(WorkflowCheckpointCompatibilityError) as exc_info:
        executable.resume(
            WorkflowResumeRequest(value={"action": "confirm"}, checkpoint_id="future-v99"),
            context=context,
        )
    assert exc_info.value.code == "WORKFLOW_CHECKPOINT_INCOMPATIBLE"
