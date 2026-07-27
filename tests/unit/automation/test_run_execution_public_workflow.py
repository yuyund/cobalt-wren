"""Django Run lifecycle tests for the public prepared-workflow execution path."""
from __future__ import annotations

import pytest

from cobalt_wren.api.engine import EnginePreparedWorkflow
from cobalt_wren.apps.automation.models.run import Run, RunStatus
from cobalt_wren.apps.automation.models.workflow import Workflow
from cobalt_wren.apps.automation.services import runs as run_services
from cobalt_wren.core.redaction import REDACTED_VALUE
from cobalt_wren.core.result_safety import safe_run_output_payload
from tests.support.recording_event_sink import RecordingEventSink


class PreparedWorkflowServices:
    def __init__(self, prepared: EnginePreparedWorkflow) -> None:
        self.prepared = prepared

    def prepare_workflow(self, _reference):
        return self.prepared


@pytest.mark.django_db
def test_start_run_executes_public_prepared_workflow_without_graph_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    workflow = Workflow.objects.create(name="external-workflow", definition_payload={"workflow": {"kind": "acme.external"}})
    run = Run.objects.create(
        workflow=workflow,
        name="external-run",
        input_payload={"request_id": "REQ-20", "secret": "abc123"},
    )
    sink = RecordingEventSink()
    monkeypatch.setattr(run_services.runtime_module, "build_event_sink", lambda _run: sink)

    class ExternalExecutable:
        def execute(self, payload):
            return {
                "message": f"accepted:{payload['request_id']}",
                "secret": payload["secret"],
                "path": "/tmp/private.txt",
            }

    prepared = EnginePreparedWorkflow(
        kind="acme.external",
        executable=ExternalExecutable(),
    )

    result = run_services.start_run(
        run=run,
        services=PreparedWorkflowServices(prepared),
    )
    result.run.refresh_from_db()

    assert result.run.status == RunStatus.SUCCEEDED
    assert result.execution_result is not None
    assert result.execution_result.details["execution_path"] == "public_executable"
    assert result.execution_result.output_payload["message"] == "accepted:REQ-20"
    assert result.run.output_payload == safe_run_output_payload(result.execution_result.output_payload)
    assert REDACTED_VALUE in repr(result.run.output_payload)
    assert "abc123" not in repr(result.run.output_payload)
    assert "/tmp/private.txt" not in repr(result.run.output_payload)
    assert [event.kind for event in sink.run_events] == ["run.started", "run.completed"]
    assert next(iter(sink.spans.values())).status == "succeeded"


@pytest.mark.django_db
def test_start_run_normalizes_public_workflow_failure_and_persists_safe_error(monkeypatch: pytest.MonkeyPatch) -> None:
    workflow = Workflow.objects.create(name="external-failing-workflow", definition_payload={"workflow": {"kind": "acme.external.failure"}})
    run = Run.objects.create(workflow=workflow, name="external-failing-run")
    sink = RecordingEventSink()
    monkeypatch.setattr(run_services.runtime_module, "build_event_sink", lambda _run: sink)

    class FailingExecutable:
        def execute(self, _payload):
            raise RuntimeError("Authorization: Bearer secret-token /tmp/private.txt")

    result = run_services.start_run(
        run=run,
        services=PreparedWorkflowServices(EnginePreparedWorkflow(
            kind="acme.external.failure",
            executable=FailingExecutable(),
        )),
    )
    result.run.refresh_from_db()

    assert result.run.status == RunStatus.FAILED
    assert result.execution_result is not None
    assert result.execution_result.details["execution_path"] == "public_executable"
    assert "secret-token" not in result.run.error_message
    assert "/tmp/private.txt" not in result.run.error_message
    assert [event.kind for event in sink.run_events] == ["run.started", "run.failed"]
    assert next(iter(sink.spans.values())).status == "failed"


@pytest.mark.django_db
def test_retry_run_reuses_public_prepared_workflow_path() -> None:
    workflow = Workflow.objects.create(name="external-retry-workflow", definition_payload={"workflow": {"kind": "acme.external.retry"}})
    run = Run.objects.create(
        workflow=workflow,
        name="external-retry-run",
        status=RunStatus.FAILED,
    )
    calls: list[dict[str, object]] = []

    def executable(payload):
        calls.append(dict(payload))
        return {"status": "retried"}

    result = run_services.retry_run(
        run=run,
        services=PreparedWorkflowServices(EnginePreparedWorkflow(
            kind="acme.external.retry",
            executable=executable,
        )),
    )
    result.run.refresh_from_db()

    assert result.run.status == RunStatus.SUCCEEDED
    assert calls == [{}]
    assert result.execution_result is not None
    assert result.execution_result.details["execution_path"] == "public_executable"


@pytest.mark.django_db
def test_start_run_auto_prepares_public_workflow_from_definition_payload() -> None:
    from cobalt_wren.apps.automation.services import runtime as runtime_module
    from tests.external_packages.acme_workflows.plugin import EXTERNAL_WORKFLOW_KIND, create_plugin

    raw_config = {"version": 1, "environment": "test"}
    services = runtime_module.build_run_execution_services(
        raw_config,
        plugins=(create_plugin(),),
        discover_plugins=False,
    )
    workflow = Workflow.objects.create(
        name="auto-external-workflow",
        definition_payload={
            "workflow": {
                "kind": EXTERNAL_WORKFLOW_KIND,
                "config": {"prefix": "django"},
            }
        },
    )
    first = Run.objects.create(
        workflow=workflow,
        name="auto-external-first",
        input_payload={"request_id": "REQ-30"},
    )
    second = Run.objects.create(
        workflow=workflow,
        name="auto-external-second",
        input_payload={"request_id": "REQ-31"},
    )

    first_result = run_services.start_run(run=first, services=services)
    engine = services.engine_owner.get_engine()
    second_result = run_services.start_run(run=second, services=services)

    assert first_result.run.status == RunStatus.SUCCEEDED
    assert second_result.run.status == RunStatus.SUCCEEDED
    assert first_result.execution_result is not None
    assert first_result.execution_result.details["execution_path"] == "public_executable"
    assert services.engine_owner.get_engine() is engine


@pytest.mark.django_db
def test_workflow_owned_lifecycle_events_are_not_duplicated_by_control_plane(monkeypatch: pytest.MonkeyPatch) -> None:
    workflow = Workflow.objects.create(name="workflow-owned-events", definition_payload={"workflow": {"kind": "acme.owns-events"}})
    run = Run.objects.create(workflow=workflow, name="workflow-owned-events-run")
    sink = RecordingEventSink()
    monkeypatch.setattr(run_services.runtime_module, "build_event_sink", lambda _run: sink)

    prepared = EnginePreparedWorkflow(
        kind="acme.owns-events",
        executable=lambda _payload: {"status": "ok"},
        lifecycle_events_owner="workflow",
    )
    result = run_services.start_run(
        run=run,
        services=PreparedWorkflowServices(prepared),
    )

    assert result.run.status == RunStatus.SUCCEEDED
    assert result.execution_result is not None
    assert result.execution_result.details["lifecycle_events_owner"] == "workflow"
    assert sink.run_events == []
    assert sink.spans == {}


@pytest.mark.django_db
def test_invalid_public_reference_fails_before_legacy_runtime_build(monkeypatch: pytest.MonkeyPatch) -> None:
    workflow = Workflow.objects.create(
        name="invalid-public-reference",
        definition_payload={"workflow": {"kind": "", "config": {}}},
    )
    run = Run.objects.create(workflow=workflow, name="invalid-reference-run")
    result = run_services.start_run(run=run)
    result.run.refresh_from_db()

    assert result.run.status == RunStatus.FAILED
    assert result.execution_result is not None
    assert result.execution_result.details["reason"] == "workflow_configuration_error"
