"""Integration tests for registry-driven web UI views."""

from __future__ import annotations

import pytest
from django.urls import reverse

from cobalt_wren.apps.automation.models.run import Run, RunStatus
from cobalt_wren.apps.automation.models.workflow import Workflow
from cobalt_wren.apps.automation.services import runtime as runtime_module
from tests.support.recording_event_sink import RecordingEventSink


@pytest.mark.django_db
def test_dynamic_list_and_detail_views_are_registry_driven(client) -> None:
    workflow = Workflow.objects.create(name="wf-ui")
    run = Run.objects.create(workflow=workflow, name="run-ui", status=RunStatus.PENDING)

    list_response = client.get(reverse("dynamic-list", kwargs={"model_key": "runs"}))
    detail_response = client.get(
        reverse("dynamic-detail", kwargs={"model_key": "runs", "object_id": run.pk})
    )
    unknown_response = client.get(
        reverse("dynamic-list", kwargs={"model_key": "unknown"})
    )

    assert list_response.status_code == 200
    assert detail_response.status_code == 200
    assert unknown_response.status_code == 404
    assert b"Run" in detail_response.content
    assert (
        b"Execution Spans" in detail_response.content
        or b"No spans yet" in detail_response.content
    )


@pytest.mark.django_db
def test_dynamic_action_view_dispatches_registered_action(
    client, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_completion(**_kwargs):
        return {
            "choices": [
                {
                    "message": {"content": "final summary"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 3,
                "completion_tokens": 2,
            },
            "model": "fake-provider-model",
        }

    sink = RecordingEventSink()
    monkeypatch.setattr(runtime_module, "build_event_sink", lambda _run: sink)
    services = runtime_module.build_run_execution_services_from_mapping(
        {
            "version": 1,
            "providers": {"default": {"provider": "litellm", "model": "test-model"}},
            "tools": {"allowlist": ["echo"]},
        }
    )
    monkeypatch.setattr(runtime_module, "get_run_execution_services", lambda: services)
    monkeypatch.setattr(
        "cobalt_wren.integrations.llm.litellm_client.litellm.completion",
        fake_completion,
    )

    workflow = Workflow.objects.create(
        name="wf-action",
        definition_payload={
            "workflow": {"kind": "test.unregistered.workflow"},
            "llm": {
                "enabled": True,
                "model": "test-model",
            },
            "tools": {
                "allowed": ["echo"],
            },
        },
    )
    run = Run.objects.create(
        workflow=workflow,
        name="run-action",
        status=RunStatus.PENDING,
        input_payload={"text": "summarize this"},
    )

    response = client.post(
        reverse(
            "dynamic-action",
            kwargs={"model_key": "runs", "object_id": run.pk, "action_name": "start"},
        )
    )
    run.refresh_from_db()

    assert response.status_code == 200
    assert run.status == RunStatus.FAILED
    assert run.error_message
    assert sink.run_events[-1].kind == "run.failed"


@pytest.mark.django_db
def test_dynamic_action_view_rejects_unknown_action(client) -> None:
    workflow = Workflow.objects.create(name="wf-action-404")
    run = Run.objects.create(
        workflow=workflow, name="run-action-404", status=RunStatus.PENDING
    )

    response = client.post(
        reverse(
            "dynamic-action",
            kwargs={"model_key": "runs", "object_id": run.pk, "action_name": "unknown"},
        )
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_dynamic_fragment_view_uses_registered_related_sections(client) -> None:
    workflow = Workflow.objects.create(name="wf-fragment")
    run = Run.objects.create(
        workflow=workflow, name="run-fragment", status=RunStatus.PENDING
    )

    response = client.get(
        reverse(
            "dynamic-fragment",
            kwargs={
                "model_key": "runs",
                "object_id": run.pk,
                "fragment_name": "events",
            },
        )
    )
    unknown_response = client.get(
        reverse(
            "dynamic-fragment",
            kwargs={
                "model_key": "runs",
                "object_id": run.pk,
                "fragment_name": "unknown",
            },
        )
    )

    assert response.status_code == 200
    assert b"Run Events" in response.content or b"No events yet" in response.content
    assert unknown_response.status_code == 404


@pytest.mark.django_db
def test_dynamic_action_view_rejects_policy_denied_action(client) -> None:
    workflow = Workflow.objects.create(name="wf-action-forbidden")
    run = Run.objects.create(
        workflow=workflow, name="run-action-forbidden", status=RunStatus.SUCCEEDED
    )

    response = client.post(
        reverse(
            "dynamic-action",
            kwargs={"model_key": "runs", "object_id": run.pk, "action_name": "cancel"},
        )
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_span_summary_is_rendered_as_structured_value_not_visible_raw_json(
    client,
) -> None:
    import json
    from cobalt_wren.apps.automation.models import ExecutionSpan, Run, Workflow
    from cobalt_wren.apps.automation.models.execution import (
        ExecutionSpanStatus,
        ExecutionSpanType,
    )

    workflow = Workflow.objects.create(name="structured-summary-workflow")
    run = Run.objects.create(workflow=workflow, name="structured-summary-run")
    span = ExecutionSpan.objects.create(
        run=run,
        span_type=ExecutionSpanType.LLM,
        name="llm:structured",
        status=ExecutionSpanStatus.SUCCEEDED,
        input_summary=json.dumps(
            {
                "preview": {"provider": "fake", "roles": ["system", "user"]},
                "truncated": False,
            }
        ),
        output_summary=json.dumps({"preview": "Structured response"}),
    )
    response = client.get(f"/ui/spans/{span.pk}/")
    html = response.content.decode()
    assert response.status_code == 200
    assert 'class="structured-value"' in html
    assert 'class="structured-map"' in html
    assert "Provider" in html
    assert "Roles" in html
    assert "Structured response" in html
    assert "Technical JSON" in html
    assert "{&quot;preview&quot;" not in html


@pytest.mark.django_db
def test_checkpoint_python_literal_summary_uses_structured_renderer(client) -> None:
    from cobalt_wren.apps.automation.models import (
        CheckpointMetadata,
        Run,
        Workflow,
    )

    workflow = Workflow.objects.create(name="checkpoint-structured-workflow")
    run = Run.objects.create(workflow=workflow, name="checkpoint-structured-run")
    checkpoint = CheckpointMetadata.objects.create(
        run=run,
        thread_id="checkpoint-structured-thread",
        checkpoint_id="checkpoint-structured-id",
        backend="memory",
        state_summary="{'status': 'compensated', 'attempt': 2}",
    )
    response = client.get(f"/ui/checkpoints/{checkpoint.pk}/")
    html = response.content.decode()
    assert response.status_code == 200
    assert 'class="structured-value"' in html
    assert "Status" in html
    assert "compensated" in html
    assert "Attempt" in html
    assert "{&#x27;status&#x27;" not in html


@pytest.mark.django_db
def test_artifact_summary_envelope_renders_compact_schema_with_one_json_control(
    client,
) -> None:
    from cobalt_wren.apps.automation.models import Artifact, Run, Workflow

    workflow = Workflow.objects.create(name="artifact-summary-workflow")
    run = Run.objects.create(workflow=workflow, name="artifact-summary-run")
    artifact = Artifact.objects.create(
        run=run,
        name="summary-artifact",
        kind="json",
        storage_key="summary/artifact.json",
        metadata={"status": "compensated"},
    )
    response = client.get(f"/ui/artifacts/{artifact.pk}/")
    html = response.content.decode()
    assert response.status_code == 200
    assert "Status" in html
    assert "compensated" in html
    assert "Value Type" not in html
    assert html.count("Technical JSON") == 1


@pytest.mark.django_db
def test_semantic_detail_layouts_for_span_event_artifact_and_checkpoint(client) -> None:
    import json
    from cobalt_wren.apps.automation.models import (
        Artifact,
        CheckpointMetadata,
        ExecutionSpan,
        Run,
        RunEvent,
        Workflow,
    )
    from cobalt_wren.apps.automation.models.execution import (
        ExecutionSpanStatus,
        ExecutionSpanType,
    )

    workflow = Workflow.objects.create(name="semantic-details-workflow")
    run = Run.objects.create(workflow=workflow, name="semantic-details-run")
    span = ExecutionSpan.objects.create(
        run=run,
        span_type=ExecutionSpanType.NODE,
        name="semantic-node",
        node_name="Semantic node",
        status=ExecutionSpanStatus.SUCCEEDED,
        duration_ms=123,
        input_summary=json.dumps(
            {
                "preview": {
                    "input_summary": {
                        "preview": {"preview": "user: Explain this result"}
                    }
                }
            }
        ),
        output_summary=json.dumps({"preview": "Result completed."}),
        metrics={"records": 4},
        metadata={"provider": "demo"},
    )
    event = RunEvent.objects.create(
        run=run,
        span=span,
        event_type="node.completed",
        message="Node completed",
        payload={"records": 4},
    )
    artifact = Artifact.objects.create(
        run=run,
        span=span,
        name="report",
        kind="json",
        storage_key="reports/result.json",
        metadata={"status": "ready"},
    )
    checkpoint = CheckpointMetadata.objects.create(
        run=run,
        span=span,
        thread_id="thread-1",
        checkpoint_id="checkpoint-1",
        backend="memory",
        state_summary="{'status': 'ready'}",
    )
    cases = (
        (
            f"/ui/spans/{span.pk}/",
            (
                "Overview",
                "Input",
                "Output",
                "Metrics",
                "Metadata",
                "user: Explain this result",
            ),
        ),
        (
            f"/ui/events/{event.pk}/",
            ("Overview", "Message", "Payload", "Node completed", "Records", "4"),
        ),
        (
            f"/ui/artifacts/{artifact.pk}/",
            (
                "Overview",
                "Storage",
                "Metadata",
                "reports/result.json",
                "Status",
                "ready",
            ),
        ),
        (
            f"/ui/checkpoints/{checkpoint.pk}/",
            ("Overview", "Checkpoint identity", "State", "thread-1", "Status", "ready"),
        ),
    )
    for url, expected in cases:
        response = client.get(url)
        html = response.content.decode()
        assert response.status_code == 200
        assert 'data-component="detail.facts"' in html
        assert '<h2 class="card-title">Details</h2>' not in html
        for value in expected:
            assert value in html
