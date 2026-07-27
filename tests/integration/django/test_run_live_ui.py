from __future__ import annotations
from datetime import timedelta
import pytest
from django.contrib.staticfiles import finders
from django.urls import reverse
from django.utils import timezone
from cobalt_wren.apps.automation.models import ExecutionSpan, Run, RunEvent, Workflow
from cobalt_wren.apps.automation.models.execution import ExecutionSpanStatus, ExecutionSpanType
from cobalt_wren.apps.automation.models.job import ExecutionJob, ExecutionJobOperation, ExecutionJobStatus
from cobalt_wren.apps.automation.models.run import RunStatus

@pytest.mark.django_db
def test_running_run_live_fragment_exposes_stream_and_projects_control_plane_records(client) -> None:
    now = timezone.now()
    workflow = Workflow.objects.create(name="external-package-workflow", definition_payload={"workflow": {"kind": "external.any_framework"}})
    run = Run.objects.create(workflow=workflow, name="live-run", status=RunStatus.RUNNING, started_at=now - timedelta(seconds=8))
    parent = ExecutionSpan.objects.create(run=run, span_type=ExecutionSpanType.GRAPH, name="workflow", status=ExecutionSpanStatus.SUCCEEDED, started_at=now - timedelta(seconds=8), finished_at=now - timedelta(seconds=5), duration_ms=3000)
    child = ExecutionSpan.objects.create(run=run, parent=parent, span_type=ExecutionSpanType.NODE, name="generate", node_name="Generate proposal", status=ExecutionSpanStatus.RUNNING, attempt=2, started_at=now - timedelta(seconds=4))
    RunEvent.objects.create(run=run, span=child, event_type="node.started", message="Generation started")
    heartbeat = now - timedelta(seconds=1)
    ExecutionJob.objects.create(run=run, operation=ExecutionJobOperation.START, status=ExecutionJobStatus.CLAIMED, worker_id="worker-a", heartbeat_at=heartbeat)

    response = client.get(reverse("run-live", kwargs={"object_id": run.pk}))
    html = response.content.decode()

    assert response.status_code == 200
    assert f'data-stream-url="/ui/runs/{run.pk}/stream/"' in html
    assert f'data-fragment-url="/ui/runs/{run.pk}/live/"' in html
    assert "Generate proposal" in html
    assert "Worker heartbeat" in html
    assert "node.started" in html
    assert 'data-testid="execution-timeline"' in html
    timeline_html = html.split('data-testid="execution-timeline"', 1)[1]
    assert timeline_html.index("workflow") < timeline_html.index("Generate proposal")
    assert 'data-depth="1"' in html
    assert "Attempt 2" in html
    assert 'data-extension-point="node-final-output"' in html

@pytest.mark.django_db
def test_terminal_run_live_fragment_marks_terminal_state(client) -> None:
    workflow = Workflow.objects.create(name="terminal-workflow")
    run = Run.objects.create(workflow=workflow, name="terminal-run", status=RunStatus.SUCCEEDED, started_at=timezone.now() - timedelta(seconds=2), finished_at=timezone.now())
    response = client.get(reverse("run-live", kwargs={"object_id": run.pk}))
    html = response.content.decode()
    assert response.status_code == 200
    assert 'data-terminal="true"' in html
    assert f'data-stream-url="/ui/runs/{run.pk}/stream/"' in html

@pytest.mark.django_db
def test_run_detail_uses_same_live_fragment_and_vendored_assets(client) -> None:
    workflow = Workflow.objects.create(name="detail-workflow")
    run = Run.objects.create(workflow=workflow, name="detail-run", status=RunStatus.WAITING)
    response = client.get(reverse("dynamic-detail", kwargs={"model_key": "runs", "object_id": run.pk}))
    html = response.content.decode()
    assert response.status_code == 200
    assert 'id="run-live-state"' in html
    assert "Waiting for workflow action" in html
    assert "/static/cobalt_wren/vendor/tabler/tabler.min.css" in html
    assert "/static/cobalt_wren/vendor/htmx/htmx.min.js" in html
    assert "/static/cobalt_wren/live-run.js" in html
    assert finders.find("cobalt_wren/vendor/tabler/tabler.min.css")
    assert finders.find("cobalt_wren/vendor/tabler/tabler.min.js")
    assert finders.find("cobalt_wren/vendor/htmx/htmx.min.js")
    assert finders.find("cobalt_wren/theme-tokens.css")
    assert finders.find("cobalt_wren/components.css")
    assert finders.find("cobalt_wren/live-run.js")

@pytest.mark.django_db
def test_run_live_fragment_returns_404_for_missing_run(client) -> None:
    response = client.get(reverse("run-live", kwargs={"object_id": 999999}))
    assert response.status_code == 404

@pytest.mark.django_db
def test_run_live_projects_llm_previews_and_sse_terminal_event(client) -> None:
    import json
    workflow = Workflow.objects.create(name="llm-ui-workflow")
    run = Run.objects.create(
        workflow=workflow,
        name="llm-ui-run",
        status=RunStatus.SUCCEEDED,
        started_at=timezone.now() - timedelta(seconds=1),
        finished_at=timezone.now(),
    )
    ExecutionSpan.objects.create(
        run=run,
        span_type=ExecutionSpanType.LLM,
        name="llm:test-model",
        node_name="Write answer",
        status=ExecutionSpanStatus.SUCCEEDED,
        duration_ms=450,
        input_summary=json.dumps({
            "messages": [
                {"preview": {"role": "system", "preview": "Answer accurately"}},
                {"preview": {"role": "user", "preview": "Explain the result"}},
            ],
            "preview": "system: Answer accurately\nuser: Explain the result",
        }),
        output_summary=json.dumps({"length": 19, "preview": "The result is valid."}),
        metadata={"preview": {"provider": "fake", "model": "test-model"}},
        metrics={"preview": {"input_tokens": 12, "output_tokens": 7}},
    )

    detail = client.get(reverse("dynamic-detail", kwargs={"model_key": "runs", "object_id": run.pk}))
    html = detail.content.decode()
    assert detail.status_code == 200
    assert 'data-component="run.llm_conversation"' in html
    assert "Answer accurately" in html
    assert "Explain the result" in html
    assert "llm-message-system" in html
    assert "llm-message-user" in html
    assert "The result is valid." in html
    assert "fake / test-model" in html
    assert html.index('data-component="run.current_state"') < html.index('data-component="run.llm_conversation"') < html.index('data-component="run.node_output"') < html.index('data-component="run.timeline"')
    assert "Input 12 tokens" in html

    stream = client.get(reverse("run-live-stream", kwargs={"object_id": run.pk}))
    assert stream.status_code == 503
    assert stream.content == b"SSE requires ASGI"
    assert stream["Cache-Control"] == "no-store"

@pytest.mark.django_db
def test_run_live_sse_missing_run_returns_404(client) -> None:
    response = client.get(reverse("run-live-stream", kwargs={"object_id": 999999}))
    assert response.status_code == 404

@pytest.mark.django_db
def test_run_live_shows_latest_bounded_node_output(client) -> None:
    import json
    workflow = Workflow.objects.create(name="node-output-workflow")
    run = Run.objects.create(workflow=workflow, name="node-output-run", status=RunStatus.SUCCEEDED)
    ExecutionSpan.objects.create(
        run=run,
        span_type=ExecutionSpanType.NODE,
        name="finalize",
        node_name="Finalize report",
        status=ExecutionSpanStatus.SUCCEEDED,
        output_summary=json.dumps({"preview": "Report is ready for review."}),
    )
    response = client.get(reverse("dynamic-detail", kwargs={"model_key": "runs", "object_id": run.pk}))
    html = response.content.decode()
    assert response.status_code == 200
    assert 'data-component="run.node_output"' in html
    assert "Finalize report" in html
    assert "Report is ready for review." in html
    assert 'data-extension-point="node-final-output"' in html

@pytest.mark.django_db
def test_status_badges_use_renderer_semantic_mapping(client) -> None:
    workflow = Workflow.objects.create(name="status-workflow")
    run = Run.objects.create(workflow=workflow, name="failed-run", status=RunStatus.FAILED)
    response = client.get(reverse("dynamic-detail", kwargs={"model_key": "runs", "object_id": run.pk}))
    assert response.status_code == 200
    assert 'bg-red-lt text-red">Failed' in response.content.decode()

@pytest.mark.django_db
def test_run_live_recovers_role_previews_from_persisted_observability_summary(client) -> None:
    import json
    from cobalt_wren.core.summary import summarize_messages
    from cobalt_wren.integrations.observability import DjangoEventSink
    workflow = Workflow.objects.create(name="observed-role-workflow")
    run = Run.objects.create(workflow=workflow, name="observed-role-run", status=RunStatus.SUCCEEDED)
    sink = DjangoEventSink()
    span_ref = sink.span_started(
        run.pk,
        ExecutionSpanType.LLM,
        "llm:observed-model",
        node_name="Observed answer",
        metadata=(lambda summary: {
            "provider": "observed",
            "model": "observed-model",
            "input_summary": summary,
            "message_previews": summary["messages"],
        })(summarize_messages([
            {"role": "system", "content": "Keep the answer short"},
            {"role": "user", "content": "Summarize the result"},
        ])),
    )
    sink.span_completed(span_ref, output_summary=json.dumps({"preview": "Result summarized."}))
    response = client.get(reverse("dynamic-detail", kwargs={"model_key": "runs", "object_id": run.pk}))
    html = response.content.decode()
    assert response.status_code == 200
    assert "Keep the answer short" in html
    assert "Summarize the result" in html
    assert "Result summarized." in html
    assert "llm-message-system" in html
    assert "llm-message-user" in html

@pytest.mark.django_db
def test_run_live_renders_one_hundred_spans_without_specialized_template(client) -> None:
    workflow = Workflow.objects.create(name="large-timeline-workflow")
    run = Run.objects.create(workflow=workflow, name="large-timeline-run", status=RunStatus.SUCCEEDED)
    ExecutionSpan.objects.bulk_create([
        ExecutionSpan(
            run=run,
            span_type=ExecutionSpanType.NODE,
            name=f"step-{index:03d}",
            node_name=f"Step {index:03d}",
            status=ExecutionSpanStatus.SUCCEEDED,
        )
        for index in range(100)
    ])
    response = client.get(reverse("run-live", kwargs={"object_id": run.pk}))
    html = response.content.decode()
    assert response.status_code == 200
    assert html.count('class="run-timeline-item"') == 100
    assert "Step 000" in html
    assert "Step 099" in html

@pytest.mark.django_db
def test_run_live_empty_states_and_responsive_contract(client) -> None:
    workflow = Workflow.objects.create(name="empty-workflow")
    run = Run.objects.create(workflow=workflow, name="empty-run", status=RunStatus.PENDING)
    response = client.get(reverse("dynamic-detail", kwargs={"model_key": "runs", "object_id": run.pk}))
    html = response.content.decode()
    assert response.status_code == 200
    assert "No LLM interaction recorded" in html
    assert "No node output recorded" in html
    assert "No execution spans yet" in html
    assert "run-live-metrics" in html
    assert "container-xl" in html

@pytest.mark.django_db
def test_run_live_stream_requires_view_permission_when_login_is_enabled(client, settings) -> None:
    settings.COBALT_WREN_REQUIRE_LOGIN = True
    workflow = Workflow.objects.create(name="protected-workflow")
    run = Run.objects.create(workflow=workflow, name="protected-run", status=RunStatus.RUNNING)
    response = client.get(reverse("run-live-stream", kwargs={"object_id": run.pk}))
    assert response.status_code == 403


@pytest.mark.django_db
def test_failed_run_live_view_renders_human_readable_failure_diagnostics(client) -> None:
    from cobalt_wren.apps.automation.models import ExecutionSpan, Run, RunEvent, Workflow
    from cobalt_wren.apps.automation.models.execution import ExecutionSpanStatus, ExecutionSpanType
    workflow = Workflow.objects.create(name="failure-diagnostic-workflow")
    run = Run.objects.create(
        workflow=workflow, name="failure-diagnostic-run", status="failed", error_message="Provisioning timed out"
    )
    span = ExecutionSpan.objects.create(
        run=run, span_type=ExecutionSpanType.NODE, name="provision-access", node_name="Provision access",
        status=ExecutionSpanStatus.FAILED, attempt=3, error_message="Provisioning timed out",
        input_summary='{"keys":["user_id","region"],"types":{"user_id":"str","region":"str"},"sizes":{"user_id":6,"region":14},"preview":{"user_id":"U-2048","region":"ap-northeast-1"}}',
    )
    RunEvent.objects.create(
        run=run, span=span, event_type="node.failed", level="error", node_name="Provision access",
        message="Provisioning timed out", payload={"retryable": False, "operation": "provision_access"},
    )
    response = client.get(f"/ui/runs/{run.pk}/")
    html = response.content.decode()
    assert response.status_code == 200
    assert 'data-component="run.failure_diagnostic"' in html
    for expected in ("Failure diagnostics", "Provisioning timed out", "Provision access", "Attempt", "3", "Input at failure", "U-2048", "ap-northeast-1", "Failure event", "node.failed", "Retryable", "Operation"):
        assert expected in html
    assert "Value Type" not in html
    assert "Keys" not in html


@pytest.mark.django_db
def test_successful_run_live_view_omits_failure_diagnostics(client) -> None:
    from cobalt_wren.apps.automation.models import Run, Workflow
    workflow = Workflow.objects.create(name="successful-diagnostic-workflow")
    run = Run.objects.create(workflow=workflow, name="successful-diagnostic-run", status="succeeded")
    response = client.get(f"/ui/runs/{run.pk}/")
    assert response.status_code == 200
    assert 'data-component="run.failure_diagnostic"' not in response.content.decode()


@pytest.mark.django_db
def test_run_live_renders_latest_native_progress_and_metrics(client) -> None:
    workflow = Workflow.objects.create(name="native-telemetry-workflow")
    run = Run.objects.create(workflow=workflow, name="native-telemetry-run", status=RunStatus.RUNNING)
    RunEvent.objects.create(
        run=run,
        event_type="semantic.native.progress",
        message="Processing documents",
        payload={"current": 3, "total": 10, "percent": 30.0},
    )
    RunEvent.objects.create(
        run=run,
        event_type="semantic.native.metric",
        message="Metric recorded",
        payload={"name": "documents.processed", "value": 3, "unit": "documents"},
    )
    response = client.get(reverse("run-live", kwargs={"object_id": run.pk}))
    html = response.content.decode()
    assert response.status_code == 200
    assert 'data-component="run.native_telemetry"' in html
    assert 'data-testid="native-progress"' in html
    assert "Processing documents" in html
    assert "3 / 10" in html
    assert "30.0%" in html
    assert "documents.processed" in html
    assert "3 documents" in html
