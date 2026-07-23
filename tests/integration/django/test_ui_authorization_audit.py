from __future__ import annotations

import pytest
from django.contrib.auth.models import Permission, User
from django.test import override_settings
from django.urls import reverse

from langgraph_automation.apps.automation.models import OperationAuditLog, Run, Workflow


@pytest.mark.django_db
def test_protected_ui_redirects_anonymous_user(client) -> None:
    with override_settings(LANGGRAPH_AUTOMATION_REQUIRE_LOGIN=True):
        response = client.get(reverse("dynamic-list", kwargs={"model_key": "runs"}))
    assert response.status_code == 302
    assert "/admin/login/" in response.url


@pytest.mark.django_db
def test_run_action_requires_permission_and_audits_denial(client) -> None:
    workflow = Workflow.objects.create(name="auth-workflow")
    run = Run.objects.create(workflow=workflow, name="auth-run")
    user = User.objects.create_user("viewer", password="secret")
    client.force_login(user)
    with override_settings(LANGGRAPH_AUTOMATION_REQUIRE_LOGIN=True):
        response = client.post(reverse("dynamic-action", kwargs={"model_key": "runs", "object_id": run.pk, "action_name": "start"}))
    assert response.status_code == 403
    assert OperationAuditLog.objects.filter(actor_identifier="viewer", action="start", outcome="denied").exists()


@pytest.mark.django_db
def test_view_permission_allows_protected_list(client) -> None:
    user = User.objects.create_user("operator", password="secret")
    user.user_permissions.add(Permission.objects.get(codename="view_run"))
    client.force_login(user)
    with override_settings(LANGGRAPH_AUTOMATION_REQUIRE_LOGIN=True):
        response = client.get(reverse("dynamic-list", kwargs={"model_key": "runs"}))
    assert response.status_code == 200
