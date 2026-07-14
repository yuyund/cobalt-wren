"""Execution dispatch tests."""

from __future__ import annotations

import pytest

from langgraph_automation.apps.automation.models.run import Run
from langgraph_automation.apps.automation.models.workflow import Workflow
from langgraph_automation.apps.automation.services.execution import dispatch_run_execution


@pytest.mark.django_db
def test_dispatch_run_execution_returns_normalized_result() -> None:
    workflow = Workflow.objects.create(name='wf-dispatch')
    run = Run.objects.create(workflow=workflow, name='run-dispatch')

    result = dispatch_run_execution(run)

    assert result.status == 'succeeded'
    assert result.output_payload['summary'] == 'minimal LangGraph execution completed'
    assert result.last_node_name == 'summarizer'
