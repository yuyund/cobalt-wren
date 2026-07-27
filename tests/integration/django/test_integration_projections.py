from __future__ import annotations

from typing import TypedDict

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from cobalt_wren.api.workflow import WorkflowExecutionContext
from cobalt_wren.apps.automation.models import (
    ExecutionSpan,
    IntegrationProjectionRecord,
    Run,
    Workflow,
)
from cobalt_wren.integrations.langgraph import integrate_langgraph
from cobalt_wren.integrations.observability.django_event_sink import DjangoEventSink


class State(TypedDict, total=False):
    message: str


@pytest.mark.django_db
def test_langgraph_projections_persist_and_render_without_framework_branch(client) -> None:
    workflow = Workflow.objects.create(name="projection-workflow")
    run = Run.objects.create(workflow=workflow, name="projection-run", thread_id="projection-thread")

    def process(state: State) -> State:
        return {"message": state["message"].upper()}

    graph = StateGraph(State)
    graph.add_node("process", process)
    graph.add_edge(START, "process")
    graph.add_edge("process", END)
    executable = integrate_langgraph(graph.compile(checkpointer=InMemorySaver()), workflow_kind="projection.demo")

    result = executable.execute(
        {"message": "hello"},
        context=WorkflowExecutionContext(
            run_id=run.pk,
            thread_id=run.thread_id,
            event_sink=DjangoEventSink(),
        ),
    )

    assert result.output == {"message": "HELLO"}
    records = IntegrationProjectionRecord.objects.filter(run=run)
    assert records.filter(schema_id="langgraph.task.v1").count() == 2
    assert records.filter(schema_id="langgraph.checkpoint_ref.v1").exists()
    task_records = records.filter(schema_id="langgraph.task.v1").order_by("sequence")
    assert set(task_records.values_list("projection_kind", flat=True)) == {"snapshot"}
    assert set(task_records.values_list("subject_kind", flat=True)) == {"execution_unit"}
    assert set(task_records.values_list("subject_external_id", flat=True)) == {"process"}
    checkpoint_records = records.filter(schema_id="langgraph.checkpoint_ref.v1")
    assert set(checkpoint_records.values_list("projection_kind", flat=True)) == {"reference"}
    assert set(checkpoint_records.values_list("subject_kind", flat=True)) == {"checkpoint"}
    span = ExecutionSpan.objects.get(run=run, node_name="process")
    assert records.filter(span=span, owner_kind="execution_unit").count() == 2

    run_page = client.get(f"/ui/runs/{run.pk}/")
    span_page = client.get(f"/ui/spans/{span.pk}/")
    run_html = run_page.content.decode()
    span_html = span_page.content.decode()
    assert run_page.status_code == 200
    assert span_page.status_code == 200
    assert 'data-component="integration.projection"' in run_html
    assert 'data-schema-id="langgraph.task.v1"' in run_html
    assert 'data-component="integration.summary"' in run_html
    assert 'href="#integration-langgraph"' in run_html
    assert "Execution units" in run_html
    assert "Projections" in run_html
    assert 'data-component="integration.current-state"' in run_html
    assert 'data-component="integration.timeline"' in run_html
    assert 'data-component="integration.technical-projections"' in run_html
    assert "process" in run_html
    assert "succeeded" in run_html
    assert "LangGraph node: process" in run_html
    assert 'data-schema-id="langgraph.task.v1"' in span_html


@pytest.mark.django_db
def test_projection_persistence_redacts_and_bounds_payload() -> None:
    from cobalt_wren.apps.automation.services.integration_projections import record_integration_projection

    workflow = Workflow.objects.create(name="projection-safe-workflow")
    run = Run.objects.create(workflow=workflow, name="projection-safe-run")
    record = record_integration_projection(
        run=run,
        integration_id="opaque",
        schema_id="opaque.detail.v1",
        owner_kind="run",
        payload={"api_token": "secret", "values": list(range(150))},
    )

    assert record.payload["api_token"] == "***REDACTED***"
    assert record.byte_size <= 64 * 1024
    assert record.truncated is True
    assert record.expires_at > record.created_at


@pytest.mark.django_db
def test_projection_semantics_validate_and_preserve_subject_identity() -> None:
    from django.utils import timezone

    from cobalt_wren.apps.automation.services.integration_projections import (
        record_integration_projection,
    )

    workflow = Workflow.objects.create(name="projection-semantics-workflow")
    run = Run.objects.create(workflow=workflow, name="projection-semantics-run")
    occurred_at = timezone.now()
    record = record_integration_projection(
        run=run,
        integration_id="opaque",
        schema_id="opaque.unit.v1",
        owner_kind="run",
        projection_kind="snapshot",
        subject_kind="execution_unit",
        subject_external_id="unit-a",
        sequence=7,
        occurred_at=occurred_at,
        payload={"status": "running"},
    )

    assert record.projection_kind == "snapshot"
    assert record.subject_kind == "execution_unit"
    assert record.subject_external_id == "unit-a"
    assert record.sequence == 7
    assert record.occurred_at == occurred_at

    with pytest.raises(ValueError):
        record_integration_projection(
            run=run,
            integration_id="opaque",
            schema_id="opaque.invalid.v1",
            owner_kind="run",
            projection_kind="invalid",
            payload={},
        )
