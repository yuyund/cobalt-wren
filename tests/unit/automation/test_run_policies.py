'''Policy tests for run lifecycle decisions.'''

from __future__ import annotations

import pytest

from langgraph_automation.apps.automation.models.run import Run, RunStatus
from langgraph_automation.apps.automation.models.workflow import Workflow
from langgraph_automation.apps.automation.policies.runs import can_cancel_run, can_resume_run, can_retry_run, can_start_run


@pytest.mark.django_db
def test_pending_run_can_start() -> None:
    workflow = Workflow.objects.create(name='wf-start')
    run = Run.objects.create(workflow=workflow, name='run-start', status=RunStatus.PENDING)
    assert can_start_run(None, run).allowed is True


@pytest.mark.django_db
def test_waiting_run_can_cancel_and_resume() -> None:
    workflow = Workflow.objects.create(name='wf-waiting')
    run = Run.objects.create(workflow=workflow, name='run-waiting', status=RunStatus.WAITING)
    assert can_cancel_run(None, run).allowed is True
    assert can_resume_run(None, run).allowed is True
    assert can_retry_run(None, run).allowed is False


@pytest.mark.django_db
def test_succeeded_run_cannot_cancel_or_resume() -> None:
    workflow = Workflow.objects.create(name='wf-complete')
    run = Run.objects.create(workflow=workflow, name='run-complete', status=RunStatus.SUCCEEDED)
    assert can_cancel_run(None, run).allowed is False
    assert can_resume_run(None, run).allowed is False


@pytest.mark.django_db
def test_failed_run_can_retry_but_not_resume() -> None:
    workflow = Workflow.objects.create(name='wf-retry')
    run = Run.objects.create(workflow=workflow, name='run-retry', status=RunStatus.FAILED)
    assert can_resume_run(None, run).allowed is False
    assert can_retry_run(None, run).allowed is True


@pytest.mark.django_db
def test_timed_out_run_can_retry() -> None:
    workflow = Workflow.objects.create(name='wf-timeout-retry')
    run = Run.objects.create(workflow=workflow, name='run-timeout-retry', status=RunStatus.TIMED_OUT)
    assert can_retry_run(None, run).allowed is True
