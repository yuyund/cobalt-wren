"""Official LlamaIndex Workflows integration tests."""

from __future__ import annotations

import pytest
from workflows import Workflow, step
from workflows.events import Event, StartEvent, StopEvent

from cobalt_wren.api.integrations import IntegrationContext
from cobalt_wren.api.workflow import WorkflowExecutionContext
from cobalt_wren.integrations.llamaindex_workflows import (
    integrate_llamaindex_workflow,
)
from cobalt_wren.integrations.workflows.definitions import (
    LLAMAINDEX_WORKFLOWS_INTEGRATION,
)
from cobalt_wren.integrations.workflows.llamaindex_provider import (
    LLAMAINDEX_WORKFLOWS_PROVIDER,
)
from tests.support.recording_event_sink import RecordingEventSink


class _Intermediate(Event):
    value: int


class _DemoWorkflow(Workflow):
    @step
    async def validate(self, ev: StartEvent) -> _Intermediate:
        return _Intermediate(value=int(ev.get("value", 0)) + 1)

    @step
    async def complete(self, ev: _Intermediate) -> StopEvent:
        return StopEvent(result={"answer": ev.value + 1})


class _FailingWorkflow(Workflow):
    @step
    async def fail(self, ev: StartEvent) -> StopEvent:
        del ev
        raise ValueError("unsafe workflow detail")


def test_llamaindex_definition_is_central_and_observable() -> None:
    assert LLAMAINDEX_WORKFLOWS_PROVIDER.definition is LLAMAINDEX_WORKFLOWS_INTEGRATION
    assert LLAMAINDEX_WORKFLOWS_INTEGRATION.capability("step_observability") is not None
    assert LLAMAINDEX_WORKFLOWS_INTEGRATION.capability("resume") is not None
    assert LLAMAINDEX_WORKFLOWS_INTEGRATION.capability("resume").support.value == "none"


def test_llamaindex_provider_projects_steps_and_events() -> None:
    sink = RecordingEventSink()
    executable = integrate_llamaindex_workflow(
        _DemoWorkflow(timeout=5),
        workflow_kind="acme.llamaindex",
    )

    result = executable.execute(
        {"value": 1},
        context=WorkflowExecutionContext(
            run_id=21,
            thread_id="llama-run",
            event_sink=sink,
        ),
    )

    assert result.output == {"answer": 3}
    assert result.metadata["integration_id"] == "llamaindex-workflows"
    assert result.metadata["completed_steps"] == ["validate", "complete"]
    spans = list(sink.spans.values())
    assert [span.name for span in spans] == ["validate", "complete"]
    assert [span.status for span in spans] == ["succeeded", "succeeded"]
    step_records = [
        item
        for item in sink.integration_projections
        if item["schema_id"] == "llamaindex.step.v1"
    ]
    event_records = [
        item
        for item in sink.integration_projections
        if item["schema_id"] == "llamaindex.event.v1"
    ]
    assert len(step_records) == 4
    assert {item["payload"]["status"] for item in step_records} == {
        "running",
        "succeeded",
    }
    assert all(item["projection_kind"] == "snapshot" for item in step_records)
    assert {item["subject_external_id"] for item in step_records} == {"validate", "complete"}
    assert any(item["payload"]["event_type"] == "StopEvent" for item in event_records)


def test_llamaindex_failure_closes_started_step_span() -> None:
    sink = RecordingEventSink()
    executable = LLAMAINDEX_WORKFLOWS_PROVIDER.wrap(
        _FailingWorkflow(timeout=5),
        context=IntegrationContext(workflow_kind="acme.llamaindex.failure"),
    )

    with pytest.raises(Exception):
        executable.execute(
            {},
            context=WorkflowExecutionContext(
                run_id=22,
                thread_id="llama-failure",
                event_sink=sink,
            ),
        )

    spans = list(sink.spans.values())
    assert [span.name for span in spans] == ["fail"]
    assert [span.status for span in spans] == ["failed"]
    failure_events = [
        item
        for item in sink.integration_projections
        if item["schema_id"] == "llamaindex.event.v1"
        and item["payload"]["event_type"] == "WorkflowFailedEvent"
    ]
    assert len(failure_events) == 1
    failed_snapshots = [
        item
        for item in sink.integration_projections
        if item["schema_id"] == "llamaindex.step.v1"
        and item["payload"].get("status") == "failed"
    ]
    assert len(failed_snapshots) == 1


def test_llamaindex_provider_rejects_non_workflow_target() -> None:
    with pytest.raises(TypeError):
        LLAMAINDEX_WORKFLOWS_PROVIDER.wrap(
            object(),
            context=IntegrationContext(workflow_kind="invalid"),
        )


def test_llamaindex_execute_works_inside_existing_event_loop() -> None:
    import asyncio

    executable = integrate_llamaindex_workflow(
        _DemoWorkflow(timeout=5),
        workflow_kind="acme.llamaindex.loop",
    )

    async def invoke() -> dict[str, object]:
        result = executable.execute(
            {"value": 2},
            context=WorkflowExecutionContext(thread_id="loop"),
        )
        return dict(result.output)

    assert asyncio.run(invoke()) == {"answer": 4}
