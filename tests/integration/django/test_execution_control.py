from __future__ import annotations

from threading import Event, Thread
import time

import pytest

from cobalt_wren.api.engine import EnginePreparedWorkflow
from cobalt_wren.api.workflow import WorkflowExecutionContext
from cobalt_wren.apps.automation.models import Run, RunStatus, Workflow
from cobalt_wren.apps.automation.services.execution import dispatch_prepared_workflow_execution
from cobalt_wren.apps.automation.services.runs import cancel_run
from tests.support.recording_event_sink import RecordingEventSink


class CooperativeBlockingWorkflow:
    def __init__(self, started: Event) -> None:
        self.started = started

    def execute(self, input_payload, *, context: WorkflowExecutionContext):
        assert context.control is not None
        self.started.set()
        while True:
            context.control.check()
            time.sleep(0.005)


class CooperativeTimeoutWorkflow:
    def execute(self, input_payload, *, context: WorkflowExecutionContext):
        assert context.control is not None
        while True:
            context.control.check()
            time.sleep(0.005)


@pytest.mark.django_db(transaction=True)
def test_cancel_run_propagates_to_cooperative_external_workflow() -> None:
    workflow = Workflow.objects.create(name="control-cancel")
    run = Run.objects.create(workflow=workflow, name="control-cancel-run", status=RunStatus.RUNNING)
    started = Event()
    sink = RecordingEventSink()
    prepared = EnginePreparedWorkflow(kind="test.cooperative", executable=CooperativeBlockingWorkflow(started))
    observed: list[object] = []

    thread = Thread(target=lambda: observed.append(dispatch_prepared_workflow_execution(run, prepared_workflow=prepared, event_sink=sink)))
    thread.start()
    assert started.wait(timeout=2)
    cancel_run(run=run)
    thread.join(timeout=2)

    assert not thread.is_alive()
    assert observed[0].status == RunStatus.CANCELLED
    run.refresh_from_db()
    assert run.status == RunStatus.CANCELLED
    assert any(event.kind == "run.cancelled" for event in sink.run_events)


@pytest.mark.django_db
def test_deadline_propagates_as_timed_out_status() -> None:
    workflow = Workflow.objects.create(name="control-timeout")
    run = Run.objects.create(workflow=workflow, name="control-timeout-run", status=RunStatus.RUNNING)
    prepared = EnginePreparedWorkflow(
        kind="test.timeout",
        executable=CooperativeTimeoutWorkflow(),
        extra={"timeout_seconds": 0.02},
    )
    result = dispatch_prepared_workflow_execution(run, prepared_workflow=prepared)
    assert result.status == RunStatus.TIMED_OUT
    assert result.details["error_code"] == "WORKFLOW_TIMED_OUT"
