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

    result = can_start_run(None, run)

    assert result.allowed is True


@pytest.mark.django_db
def test_running_run_can_cancel() -> None:
    workflow = Workflow.objects.create(name='wf-cancel')
    run = Run.objects.create(workflow=workflow, name='run-cancel', status=RunStatus.RUNNING)

    result = can_cancel_run(None, run)

    assert result.allowed is True


@pytest.mark.django_db
def test_succeeded_run_cannot_cancel() -> None:
    workflow = Workflow.objects.create(name='wf-cancel-block')
    run = Run.objects.create(workflow=workflow, name='run-cancel-block', status=RunStatus.SUCCEEDED)

    result = can_cancel_run(None, run)

    assert result.allowed is False


@pytest.mark.django_db
def test_failed_run_can_retry_but_resume_is_unsupported() -> None:
    workflow = Workflow.objects.create(name='wf-retry')
    run = Run.objects.create(workflow=workflow, name='run-retry', status=RunStatus.FAILED)

    assert can_resume_run(None, run).allowed is False
    assert can_retry_run(None, run).allowed is True
