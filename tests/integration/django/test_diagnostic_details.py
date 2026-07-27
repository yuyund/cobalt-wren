from __future__ import annotations
import pytest
from django.test import override_settings
from cobalt_wren.apps.automation.models import (
    DiagnosticPayload,
    OperationAuditLog,
    Run,
    Workflow,
)
from cobalt_wren.apps.automation.services.diagnostics import (
    record_diagnostic_payload,
)


@pytest.mark.django_db
def test_run_detail_exposes_lazy_inspect_and_audits_access(client) -> None:
    workflow = Workflow.objects.create(name="diagnostic-inspect-workflow")
    run = Run.objects.create(
        workflow=workflow,
        name="diagnostic-inspect-run",
        output_payload={
            "status": "compensated",
            "results": [{"step": "reserve", "status": "ok"}],
        },
    )
    page = client.get(f"/ui/runs/{run.pk}/")
    html = page.content.decode()
    assert page.status_code == 200
    assert "Inspect details" in html
    url = f"/ui/diagnostics/runs/{run.pk}/output_payload_summary/"
    detail = client.get(url)
    detail_html = detail.content.decode()
    assert detail.status_code == 200
    assert 'data-component="diagnostic.detail"' in detail_html
    assert "compensated" in detail_html
    assert "reserve" in detail_html
    assert "Technical JSON" in detail_html
    audit = OperationAuditLog.objects.filter(
        action="diagnostic.inspect", target_type="runs", target_id=str(run.pk)
    ).latest("created_at")
    assert audit.outcome == "succeeded"


@pytest.mark.django_db
def test_retained_snapshot_takes_precedence_over_raw_source(client) -> None:
    workflow = Workflow.objects.create(name="diagnostic-snapshot-workflow")
    run = Run.objects.create(
        workflow=workflow,
        name="diagnostic-snapshot-run",
        output_payload={"status": "raw"},
    )
    record_diagnostic_payload(
        target_type="runs",
        target_id=run.pk,
        field_name="output_payload_summary",
        value={"status": "snapshot", "api_token": "secret"},
        run=run,
    )
    response = client.get(f"/ui/diagnostics/runs/{run.pk}/output_payload_summary/")
    html = response.content.decode()
    assert response.status_code == 200
    assert "snapshot" in html
    assert "raw" not in html
    assert "secret" not in html
    assert "Redacted" in html


@pytest.mark.django_db
@override_settings(COBALT_WREN_REQUIRE_LOGIN=True)
def test_diagnostic_detail_requires_target_view_permission(client) -> None:
    workflow = Workflow.objects.create(name="diagnostic-denied-workflow")
    run = Run.objects.create(
        workflow=workflow,
        name="diagnostic-denied-run",
        output_payload={"status": "ready"},
    )
    response = client.get(f"/ui/diagnostics/runs/{run.pk}/output_payload_summary/")
    assert response.status_code == 403
    assert OperationAuditLog.objects.filter(
        action="diagnostic.inspect", outcome="denied"
    ).exists()


@pytest.mark.django_db
def test_recorded_diagnostic_has_expiry_and_bounded_payload() -> None:
    workflow = Workflow.objects.create(name="diagnostic-expiry-workflow")
    run = Run.objects.create(workflow=workflow, name="diagnostic-expiry-run")
    diagnostic = record_diagnostic_payload(
        target_type="runs",
        target_id=run.pk,
        field_name="input_payload_summary",
        value={"values": list(range(150))},
        run=run,
    )
    assert diagnostic.expires_at > diagnostic.created_at
    assert diagnostic.byte_size <= 64 * 1024
    assert diagnostic.truncated is True
    assert DiagnosticPayload.objects.filter(pk=diagnostic.pk).exists()
