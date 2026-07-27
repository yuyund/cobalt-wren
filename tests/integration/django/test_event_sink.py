"""Integration tests for the Django observability sink."""

from __future__ import annotations

import pytest

from cobalt_wren.core.redaction import REDACTED_VALUE
from cobalt_wren.apps.automation.models.event import RunEventLevel
from cobalt_wren.apps.automation.models.execution import (
    ExecutionSpanStatus,
    ExecutionSpanType,
)
from cobalt_wren.apps.automation.models.run import Run, RunStatus
from cobalt_wren.apps.automation.models.workflow import Workflow
from cobalt_wren.integrations.observability import DjangoEventSink


@pytest.mark.django_db
def test_event_sink_creates_events_spans_and_metadata() -> None:
    workflow = Workflow.objects.create(name="wf-sink")
    run = Run.objects.create(
        workflow=workflow, name="run-sink", status=RunStatus.PENDING
    )
    sink = DjangoEventSink()

    sink.run_started(run.pk, message="run started", payload={"trace_id": "abc"})
    graph_ref = sink.span_started(
        run.pk,
        ExecutionSpanType.GRAPH,
        "demo-graph",
        node_name="graph",
        metadata={"phase": "demo"},
    )
    node_ref = sink.node_started(run.pk, "planner", parent=graph_ref)
    sink.node_completed(node_ref, output_summary="node ok", metrics={"step": 1})
    semantic_event = sink.semantic_event(
        run.pk,
        "planner.decision_made",
        message="planner selected route",
        payload={"route": "plan"},
        parent_span=node_ref,
        node_name="planner",
    )
    llm_ref = sink.llm_started(
        run.pk,
        "demo-llm",
        node_name="planner",
        parent=node_ref,
        provider="fake",
        model="fake",
    )
    sink.llm_failed(llm_ref, error_message="llm failed", metrics={"retryable": False})
    sink.artifact_created(
        run.pk,
        "artifact-1",
        "report",
        "text",
        span=node_ref,
        metadata={"x": 1},
        content_type="text/markdown",
        size=42,
    )
    sink.checkpoint_saved(
        run.pk,
        "thread-1",
        "checkpoint-1",
        "sqlite",
        span=node_ref,
        state_summary="state",
        checkpoint_namespace="demo",
    )
    sink.span_completed(graph_ref, output_summary="graph ok", metrics={"ok": True})

    run.refresh_from_db()
    assert run.last_span_name == "demo-graph"
    assert run.last_event_at is not None

    graph_span = run.spans.get(name="demo-graph")
    node_span = run.spans.get(name="planner")
    llm_span = run.spans.get(name="demo-llm")

    assert graph_span.status == ExecutionSpanStatus.SUCCEEDED
    assert node_span.parent_id == graph_span.pk
    assert node_span.status == ExecutionSpanStatus.SUCCEEDED
    assert node_span.output_summary == "node ok"
    assert llm_span.parent_id == node_span.pk
    assert llm_span.status == ExecutionSpanStatus.FAILED
    assert llm_span.error_message == "llm failed"
    assert run.events.filter(
        event_type="run.started", level=RunEventLevel.INFO
    ).exists()
    assert run.events.filter(
        event_type="semantic.planner.decision_made", level=RunEventLevel.INFO
    ).exists()
    assert run.events.filter(
        event_type="semantic.planner.decision_made", span=node_span
    ).exists()
    assert semantic_event.message == "planner selected route"
    assert semantic_event.payload == {"route": "plan"}
    assert semantic_event.span_id == node_span.pk
    assert run.events.filter(
        event_type="llm.failed", level=RunEventLevel.ERROR
    ).exists()
    artifact = run.artifacts.get(name="report")
    checkpoint = run.checkpoint_metadata.get(checkpoint_id="checkpoint-1")
    assert artifact.content_type == "text/markdown"
    assert artifact.size == 42
    assert checkpoint.checkpoint_namespace == "demo"


@pytest.mark.django_db
def test_event_sink_bounds_and_redacts_long_payloads_and_summaries() -> None:
    workflow = Workflow.objects.create(name="wf-sink-safe")
    run = Run.objects.create(
        workflow=workflow, name="run-sink-safe", status=RunStatus.PENDING
    )
    sink = DjangoEventSink()

    long_secret = "Authorization: Bearer " + ("x" * 500)
    graph_ref = sink.span_started(
        run.pk,
        ExecutionSpanType.GRAPH,
        "demo-graph-safe",
        node_name="graph",
        metadata={"secret_token": long_secret},
    )
    node_ref = sink.node_started(run.pk, "planner", parent=graph_ref)
    sink.span_completed(
        graph_ref,
        output_summary=long_secret,
        metrics={"latency_ms": 123, "nested": {"password": long_secret}},
        metadata={"raw_path": "/tmp/secret.txt"},
    )
    sink.artifact_created(
        run.pk,
        "run-123/output.md",
        "report",
        "text",
        span=node_ref,
        metadata={"trace_id": long_secret},
    )

    run.refresh_from_db()
    graph_span = run.spans.get(name="demo-graph-safe")
    assert len(graph_span.output_summary) <= 300
    assert "x" * 100 not in graph_span.output_summary
    assert REDACTED_VALUE in graph_span.input_summary
    assert REDACTED_VALUE in str(graph_span.metadata)
    assert REDACTED_VALUE in str(graph_span.metrics)
    assert run.artifacts.filter(storage_key="run-123/output.md").exists()


@pytest.mark.django_db
def test_event_sink_redacts_secret_like_values_from_payloads_and_metadata() -> None:
    workflow = Workflow.objects.create(name="wf-sink-secret")
    run = Run.objects.create(
        workflow=workflow, name="run-sink-secret", status=RunStatus.PENDING
    )
    sink = DjangoEventSink()

    secret = "Authorization: Bearer secret-token /tmp/secret.txt"

    semantic_event = sink.semantic_event(
        run.pk,
        "planner.decision_made",
        message="planner selected route",
        payload={"route": "plan", "token": secret},
    )
    graph_ref = sink.span_started(
        run.pk,
        ExecutionSpanType.GRAPH,
        "demo-graph-secret",
        node_name="graph",
        metadata={"api_key": secret},
    )
    sink.span_completed(
        graph_ref,
        output_summary=secret,
        metrics={"nested": {"password": secret}},
        metadata={"raw_path": "/tmp/secret.txt"},
    )
    artifact = sink.artifact_created(
        run.pk, "artifact-2", "report", "text", metadata={"trace_id": secret}
    )
    checkpoint = sink.checkpoint_saved(
        run.pk, "thread-2", "checkpoint-2", "sqlite", state_summary=secret
    )

    run.refresh_from_db()
    graph_span = run.spans.get(name="demo-graph-secret")
    artifact.refresh_from_db()
    checkpoint.refresh_from_db()

    assert semantic_event.payload == {"route": "plan", "token": "***REDACTED***"}
    assert secret not in str(graph_span.metadata)
    assert secret not in str(graph_span.metrics)
    assert secret not in str(artifact.metadata)
    assert secret not in checkpoint.state_summary
    assert "/tmp/secret.txt" not in checkpoint.state_summary


@pytest.mark.django_db
def test_event_sink_rejects_unsafe_artifact_storage_keys() -> None:
    workflow = Workflow.objects.create(name="wf-sink-unsafe")
    run = Run.objects.create(
        workflow=workflow, name="run-sink-unsafe", status=RunStatus.PENDING
    )
    sink = DjangoEventSink()

    with pytest.raises(ValueError):
        sink.artifact_created(run.pk, "/tmp/output.md", "report", "text")


@pytest.mark.django_db
def test_event_sink_records_inspectable_diagnostics_without_double_summarizing() -> (
    None
):
    from cobalt_wren.apps.automation.models import (
        DiagnosticPayload,
        Run,
        Workflow,
    )

    workflow = Workflow.objects.create(name="diagnostic-event-sink-workflow")
    run = Run.objects.create(workflow=workflow, name="diagnostic-event-sink-run")
    sink = DjangoEventSink()
    span_ref = sink.span_started(
        run.pk,
        "tool",
        "diagnostic-tool",
        metadata={"operation": "execute", "api_token": "secret"},
    )
    span = sink.span_completed(
        span_ref,
        output_summary="completed",
        metrics={"duration_ms": 14, "records": 3},
        metadata={"provider": "demo", "model": "test-model"},
    )
    span.refresh_from_db()
    assert span.metrics == {"duration_ms": 14, "records": 3}
    assert span.metadata == {"provider": "demo", "model": "test-model"}
    snapshots = DiagnosticPayload.objects.filter(target_type="spans", target_id=span.pk)
    assert snapshots.filter(field_name="input_summary").exists()
    assert snapshots.filter(field_name="output_summary").exists()
    assert snapshots.filter(field_name="metrics_summary").exists()
    assert snapshots.filter(field_name="metadata_summary").exists()
    assert "secret" not in repr(snapshots.get(field_name="input_summary").payload)
