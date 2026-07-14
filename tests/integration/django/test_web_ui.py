'''Integration tests for registry-driven web UI views.'''

from __future__ import annotations

import pytest
from django.urls import reverse

from langgraph_automation.apps.automation.models.run import Run, RunStatus
from langgraph_automation.apps.automation.models.workflow import Workflow


@pytest.mark.django_db
def test_dynamic_list_and_detail_views_are_registry_driven(client) -> None:
    workflow = Workflow.objects.create(name='wf-ui')
    run = Run.objects.create(workflow=workflow, name='run-ui', status=RunStatus.PENDING)

    list_response = client.get(reverse('dynamic-list', kwargs={'model_key': 'runs'}))
    detail_response = client.get(reverse('dynamic-detail', kwargs={'model_key': 'runs', 'object_id': run.pk}))
    unknown_response = client.get(reverse('dynamic-list', kwargs={'model_key': 'unknown'}))

    assert list_response.status_code == 200
    assert detail_response.status_code == 200
    assert unknown_response.status_code == 404
    assert b'Run' in detail_response.content
    assert b'Execution Spans' in detail_response.content or b'No spans yet' in detail_response.content


@pytest.mark.django_db
def test_dynamic_action_view_dispatches_registered_action(client) -> None:
    workflow = Workflow.objects.create(name='wf-action')
    run = Run.objects.create(workflow=workflow, name='run-action', status=RunStatus.PENDING)

    response = client.post(reverse('dynamic-action', kwargs={'model_key': 'runs', 'object_id': run.pk, 'action_name': 'start'}))
    run.refresh_from_db()

    assert response.status_code == 200
    assert run.status == RunStatus.SUCCEEDED


@pytest.mark.django_db
def test_dynamic_action_view_rejects_unknown_action(client) -> None:
    workflow = Workflow.objects.create(name='wf-action-404')
    run = Run.objects.create(workflow=workflow, name='run-action-404', status=RunStatus.PENDING)

    response = client.post(reverse('dynamic-action', kwargs={'model_key': 'runs', 'object_id': run.pk, 'action_name': 'unknown'}))

    assert response.status_code == 404


@pytest.mark.django_db
def test_dynamic_fragment_view_uses_registered_related_sections(client) -> None:
    workflow = Workflow.objects.create(name='wf-fragment')
    run = Run.objects.create(workflow=workflow, name='run-fragment', status=RunStatus.PENDING)

    response = client.get(reverse('dynamic-fragment', kwargs={'model_key': 'runs', 'object_id': run.pk, 'fragment_name': 'events'}))
    unknown_response = client.get(reverse('dynamic-fragment', kwargs={'model_key': 'runs', 'object_id': run.pk, 'fragment_name': 'unknown'}))

    assert response.status_code == 200
    assert b'Run Events' in response.content or b'No events yet' in response.content
    assert unknown_response.status_code == 404


@pytest.mark.django_db
def test_dynamic_action_view_rejects_policy_denied_action(client) -> None:
    workflow = Workflow.objects.create(name='wf-action-forbidden')
    run = Run.objects.create(workflow=workflow, name='run-action-forbidden', status=RunStatus.SUCCEEDED)

    response = client.post(reverse('dynamic-action', kwargs={'model_key': 'runs', 'object_id': run.pk, 'action_name': 'cancel'}))

    assert response.status_code == 403
