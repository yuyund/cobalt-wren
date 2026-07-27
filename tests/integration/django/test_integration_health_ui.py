"""Django UI tests for workflow integration availability and health."""

from __future__ import annotations

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_integration_health_list_and_detail_render(client) -> None:
    list_response = client.get(reverse("integration-health-list"))
    langgraph_response = client.get(
        reverse(
            "integration-health-detail",
            kwargs={"integration_id": "langgraph"},
        )
    )
    llamaindex_response = client.get(
        reverse(
            "integration-health-detail",
            kwargs={"integration_id": "llamaindex-workflows"},
        )
    )

    assert list_response.status_code == 200
    list_html = list_response.content.decode()
    assert 'data-component="integration.health-list"' in list_html
    assert "langgraph" in list_html
    assert "llamaindex-workflows" in list_html
    assert "/ui/integrations/" in list_html

    for response, integration_id, capability in (
        (langgraph_response, "langgraph", "node_observability"),
        (llamaindex_response, "llamaindex-workflows", "step_observability"),
    ):
        assert response.status_code == 200
        html = response.content.decode()
        assert 'data-component="integration.health-detail"' in html
        assert integration_id in html
        assert capability in html
        assert "Capabilities" in html
        assert "Supported versions" in html
        assert "Provider status" in html


@pytest.mark.django_db
def test_integration_health_unknown_detail_returns_404(client) -> None:
    response = client.get(
        reverse(
            "integration-health-detail",
            kwargs={"integration_id": "unknown-integration"},
        )
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_primary_navigation_links_to_integration_health(client) -> None:
    response = client.get(reverse("dynamic-list", kwargs={"model_key": "runs"}))

    assert response.status_code == 200
    assert '<a class="nav-link" href="/ui/integrations/">Integrations</a>' in (
        response.content.decode()
    )
