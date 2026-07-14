"""Run service tests for observability failure masking."""

from __future__ import annotations

import logging

import pytest

from langgraph_automation.apps.automation.models.run import Run, RunStatus
from langgraph_automation.apps.automation.models.workflow import Workflow
from langgraph_automation.apps.automation.services import runs as run_services
from langgraph_automation.core.result_safety import safe_run_error_message
from langgraph_automation.graphs.runtime import GraphRuntime
from langgraph_automation.integrations.observability.types import ObservabilityContext
from tests.support.failing_event_sink import FailingRunFailedEventSink


@pytest.mark.django_db
def test_start_run_preserves_primary_failure_when_run_failed_observability_fails(
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workflow = Workflow.objects.create(name='wf-failure-mask')
    run = Run.objects.create(workflow=workflow, name='run-failure-mask')
    runtime = GraphRuntime(
        logger=logging.getLogger('test.run.failure-mask'),
        observability=ObservabilityContext(run_id=run.pk, thread_id='thread-1'),
        event_sink=FailingRunFailedEventSink(
            RuntimeError('Authorization: Bearer secret-token /tmp/leak.txt')
        ),
    )

    def fake_dispatch(*_args, **_kwargs):
        raise RuntimeError('primary failure Authorization: Bearer secret-token /tmp/leak.txt')

    monkeypatch.setattr(run_services, 'dispatch_run_execution', fake_dispatch)
    caplog.set_level(logging.WARNING)

    with pytest.raises(RuntimeError, match='primary failure'):
        run_services.start_run(run=run, runtime=runtime)

    run.refresh_from_db()
    assert run.status == RunStatus.FAILED
    assert run.error_message == safe_run_error_message(
        RuntimeError('primary failure Authorization: Bearer secret-token /tmp/leak.txt')
    )
    assert 'Observability failure suppressed' in caplog.text
    assert 'secret-token' not in caplog.text
    assert '/tmp/leak.txt' not in caplog.text
