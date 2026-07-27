from __future__ import annotations

from pathlib import Path
import sys

import pytest
from django.urls import reverse

ROOT = Path(__file__).parents[3]
for package in ("human_approval_workflow", "saga_workflow", "plain_python_workflow"):
    sys.path.insert(0, str(ROOT / "packages" / package / "src"))

from human_approval_workflow import create_plugin as create_approval_plugin  # noqa: E402
from saga_workflow import create_plugin as create_saga_plugin  # noqa: E402
from plain_python_workflow import create_plugin as create_plain_plugin  # noqa: E402
from cobalt_wren.apps.automation.models import Run, RunStatus, Workflow  # noqa: E402
from cobalt_wren.apps.automation.services import runtime as runtime_module  # noqa: E402
from cobalt_wren.apps.automation.services.runs import start_run  # noqa: E402


def _services(tmp_path: Path):
    return runtime_module.build_run_execution_services(
        {
            "version": 1,
            "stores": {
                "artifact": {"backend": "filesystem", "config": {"root": str(tmp_path / "artifacts")}},
                "checkpoint": {"backend": "filesystem", "config": {"root": str(tmp_path / "checkpoints")}},
            },
        },
        plugins=(create_approval_plugin(), create_saga_plugin(), create_plain_plugin()),
        discover_plugins=False,
    )


def _waiting_run(workflow_kind: str, payload: dict[str, object], services) -> Run:
    workflow = Workflow.objects.create(
        name=f"ui-{workflow_kind}",
        definition_payload={"workflow": {"kind": workflow_kind, "config": {}}},
    )
    run = Run.objects.create(workflow=workflow, name=f"run-{workflow_kind}", input_payload=payload)
    return start_run(run=run, services=services).run


@pytest.mark.django_db
def test_human_approval_schema_projects_to_forms_and_resumes(client, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    services = _services(tmp_path)
    monkeypatch.setattr(runtime_module, "get_run_execution_services", lambda: services)
    run = _waiting_run(
        "human.approval",
        {"title": "Release", "proposal": "Deploy version 2"},
        services,
    )
    assert run.status == RunStatus.WAITING

    detail = client.get(reverse("dynamic-detail", kwargs={"model_key": "runs", "object_id": run.pk}))
    html = detail.content.decode()
    assert detail.status_code == 200
    assert "Approve" in html
    assert "Reject" in html
    assert "Request revision" in html
    assert 'name="proposal"' in html
    assert 'name="checkpoint_id"' in html

    response = client.post(
        reverse("dynamic-action", kwargs={"model_key": "runs", "object_id": run.pk, "action_name": "resume-approve"}),
        {"note": "UI reviewed", "checkpoint_id": "approval-pause-0"},
    )
    run.refresh_from_db()
    assert response.status_code == 200
    assert run.status == RunStatus.SUCCEEDED
    assert run.artifacts.count() == 1
    assert run.checkpoint_metadata.count() == 1

    duplicate = client.post(
        reverse("dynamic-action", kwargs={"model_key": "runs", "object_id": run.pk, "action_name": "resume-approve"}),
        {"checkpoint_id": "approval-pause-0"},
    )
    assert duplicate.status_code == 403


@pytest.mark.django_db
def test_resume_form_validates_required_schema_fields(client, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    services = _services(tmp_path)
    monkeypatch.setattr(runtime_module, "get_run_execution_services", lambda: services)
    run = _waiting_run(
        "human.approval",
        {"title": "Contract", "proposal": "Initial wording"},
        services,
    )
    response = client.post(
        reverse("dynamic-action", kwargs={"model_key": "runs", "object_id": run.pk, "action_name": "resume-revise"}),
        {"checkpoint_id": "approval-pause-0", "proposal": ""},
    )
    run.refresh_from_db()
    assert response.status_code == 400
    assert b"Revised proposal is required" in response.content
    assert run.status == RunStatus.WAITING


@pytest.mark.django_db
def test_saga_projection_honors_checkpoint_allowed_actions(client, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    services = _services(tmp_path)
    monkeypatch.setattr(runtime_module, "get_run_execution_services", lambda: services)
    run = _waiting_run(
        "saga.order_fulfillment",
        {"order_id": "UI-SAGA-1", "failure_plan": {"provision_access": "fatal"}},
        services,
    )
    detail = client.get(reverse("dynamic-detail", kwargs={"model_key": "runs", "object_id": run.pk}))
    html = detail.content.decode()
    assert "Compensate successful branches" in html
    assert "Retry failed branches" not in html


@pytest.mark.django_db
def test_artifact_preview_download_and_list_links_use_runtime_store(client, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    services = _services(tmp_path)
    monkeypatch.setattr(runtime_module, "get_run_execution_services", lambda: services)
    run = _waiting_run(
        "plain.confirmation",
        {"subject": "Artifact", "message": "Authorization: Bearer abcdefghijklmnop"},
        services,
    )
    response = client.post(
        reverse("dynamic-action", kwargs={"model_key": "runs", "object_id": run.pk, "action_name": "resume-confirm"}),
        {"note": "done", "checkpoint_id": "awaiting-confirmation-v1"},
    )
    assert response.status_code == 200
    run.refresh_from_db()
    artifact = run.artifacts.get()

    list_response = client.get(reverse("dynamic-list", kwargs={"model_key": "runs"}))
    assert f'/ui/runs/{run.pk}/' in list_response.content.decode()

    artifact_detail = client.get(reverse("dynamic-detail", kwargs={"model_key": "artifacts", "object_id": artifact.pk}))
    assert "Preview" in artifact_detail.content.decode()
    assert "Download" in artifact_detail.content.decode()

    preview = client.get(reverse("artifact-preview", kwargs={"object_id": artifact.pk}))
    preview_html = preview.content.decode()
    assert preview.status_code == 200
    assert "confirmed" in preview_html
    assert "abcdefghijklmnop" not in preview_html
    assert "REDACTED" in preview_html

    download = client.get(reverse("artifact-download", kwargs={"object_id": artifact.pk}))
    assert download.status_code == 200
    assert download["Content-Disposition"].startswith("attachment;")
    assert download["X-Content-Type-Options"] == "nosniff"
    assert b'"decision": "confirmed"' in download.content
