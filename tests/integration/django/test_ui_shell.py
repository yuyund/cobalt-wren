from __future__ import annotations

import pytest
from django.urls import reverse

from cobalt_wren.apps.automation.models import Run, Workflow


@pytest.mark.django_db
def test_ui_shell_has_navigation_links_and_detail_links(client) -> None:
    workflow = Workflow.objects.create(name="shell-workflow")
    run = Run.objects.create(workflow=workflow, name="shell-run")
    response = client.get(reverse("dynamic-list", kwargs={"model_key": "runs"}))
    html = response.content.decode()
    assert response.status_code == 200
    assert "Automation Control Plane" in html
    for path in ("/ui/runs/", "/ui/workflows/", "/ui/artifacts/", "/ui/checkpoints/", "/ui/events/", "/ui/spans/"):
        assert f'href="{path}"' in html
    assert f'href="/ui/runs/{run.pk}/"' in html
    assert 'class="table-wrap"' in html
