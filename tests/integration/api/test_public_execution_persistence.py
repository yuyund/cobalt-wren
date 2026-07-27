from __future__ import annotations

import pytest

from cobalt_wren.api.workflow import WorkflowRequirements
from cobalt_wren.apps.automation.models.run import Run, RunStatus
from cobalt_wren.apps.automation.models.workflow import Workflow
from cobalt_wren.apps.automation.services import runs as run_services
from cobalt_wren.apps.automation.services import runtime as runtime_module
from cobalt_wren.apps.automation.services.workflow_reference import WorkflowReference
from cobalt_wren.integrations.artifact.base import ArtifactStore
from cobalt_wren.integrations.checkpoint.base import CheckpointStore
from tests.external_packages.acme_workflows.plugin import (
    EXTERNAL_WORKFLOW_KIND,
    ExternalGraph,
    create_plugin,
)
from tests.support.recording_event_sink import RecordingEventSink


@pytest.mark.django_db
def test_public_execution_persists_artifact_checkpoint_and_observability(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sink = RecordingEventSink()
    monkeypatch.setattr(runtime_module, "build_event_sink", lambda _run: sink)
    services = runtime_module.build_run_execution_services(
        {"version": 1, "environment": "test"},
        plugins=(
            create_plugin(
                requirements=WorkflowRequirements(artifact_store=True, checkpoint_store=True)
            ),
        ),
        discover_plugins=False,
    )
    workflow = Workflow.objects.create(
        name="persistent-external-workflow",
        definition_payload={
            "workflow": {"kind": EXTERNAL_WORKFLOW_KIND, "config": {"prefix": "persist"}}
        },
    )
    run = Run.objects.create(
        workflow=workflow,
        name="persistent-external-run",
        input_payload={"request_id": "REQ-PERSIST"},
    )

    result = run_services.start_run(run=run, services=services)
    result.run.refresh_from_db()

    assert result.run.status == RunStatus.SUCCEEDED
    assert result.execution_result is not None
    assert result.execution_result.output_payload["artifact_key"] == "reviews/REQ-PERSIST.txt"
    assert result.execution_result.output_payload["checkpoint_id"] == "reviewed"
    assert [event.kind for event in sink.run_events] == ["run.started", "run.completed"]
    assert next(iter(sink.spans.values())).status == "succeeded"

    prepared = services.prepare_workflow(
        WorkflowReference(kind=EXTERNAL_WORKFLOW_KIND, config={"prefix": "inspect"})
    )
    executable = prepared.executable
    assert isinstance(executable, ExternalGraph)
    assert isinstance(executable.artifact_store, ArtifactStore)
    assert isinstance(executable.checkpoint_store, CheckpointStore)
    artifact = executable.artifact_store.get("reviews/REQ-PERSIST.txt")
    checkpoint = executable.checkpoint_store.load_latest("REQ-PERSIST")
    assert artifact is not None and artifact.body == b"REQ-PERSIST"
    assert checkpoint is not None and checkpoint.body == b"REQ-PERSIST"
