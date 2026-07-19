"""Run service safety and resume semantics tests."""

from __future__ import annotations

import pytest

from langgraph_automation.apps.automation.models.run import Run, RunStatus
from langgraph_automation.apps.automation.models.workflow import Workflow
from langgraph_automation.apps.automation.services import runs as run_services
from langgraph_automation.core.redaction import REDACTED_VALUE
from langgraph_automation.core.result_safety import safe_run_error_message, safe_run_output_payload
from langgraph_automation.config.normalizer import load_normalized_package_config_from_mapping
from langgraph_automation.graphs.runner import ExecutionResult


@pytest.mark.django_db
def test_start_run_saves_safe_output_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    workflow = Workflow.objects.create(
        name='wf-safe-output',
        definition_payload={
            'llm': {'enabled': True, 'model': 'test-model'},
            'tools': {'allowed': ['echo']},
        },
    )
    run = Run.objects.create(workflow=workflow, name='run-safe-output', input_payload={'prompt': 'hello'})

    def fake_dispatch(*_args, **_kwargs):
        return ExecutionResult(
            status='succeeded',
            output_payload={
                'summary': 'done',
                'secret': 'abc123',
                'path': '/tmp/secret.txt',
                'nested': {'token': 'def456'},
            },
            message='ok',
        )

    monkeypatch.setattr(run_services, 'dispatch_run_execution', fake_dispatch)

    result = run_services.start_run(run=run)
    result.run.refresh_from_db()

    assert result.run.status == RunStatus.SUCCEEDED
    assert result.run.output_payload == safe_run_output_payload({
        'summary': 'done',
        'secret': 'abc123',
        'path': '/tmp/secret.txt',
        'nested': {'token': 'def456'},
    })
    assert REDACTED_VALUE in repr(result.run.output_payload)
    assert 'abc123' not in repr(result.run.output_payload)
    assert '/tmp/secret.txt' not in repr(result.run.output_payload)


@pytest.mark.django_db
def test_start_run_forwards_typed_package_settings_to_runtime_construction(monkeypatch: pytest.MonkeyPatch) -> None:
    workflow = Workflow.objects.create(
        name='wf-package-settings',
        definition_payload={
            'llm': {'enabled': True, 'model': 'test-model'},
            'tools': {'allowed': ['echo']},
        },
    )
    run = Run.objects.create(workflow=workflow, name='run-package-settings')
    package_settings = load_normalized_package_config_from_mapping({"version": 1})
    captured: list[object] = []

    def fake_build_graph_runtime(run_arg, *, package_settings=None):
        captured.append(package_settings)
        return object()

    def fake_dispatch_run_execution(*_args, **_kwargs):
        return ExecutionResult(status=RunStatus.SUCCEEDED, output_payload={}, message='ok')

    monkeypatch.setattr(run_services.runtime_module, 'build_graph_runtime', fake_build_graph_runtime)
    monkeypatch.setattr(run_services, 'dispatch_run_execution', fake_dispatch_run_execution)

    result = run_services.start_run(run=run, package_settings=package_settings)

    assert result.run.status == RunStatus.SUCCEEDED
    assert captured == [package_settings]


@pytest.mark.django_db
def test_retry_run_saves_safe_failed_error_message(monkeypatch: pytest.MonkeyPatch) -> None:
    workflow = Workflow.objects.create(
        name='wf-safe-error',
        definition_payload={
            'llm': {'enabled': True, 'model': 'test-model'},
            'tools': {'allowed': ['echo']},
        },
    )
    run = Run.objects.create(workflow=workflow, name='run-safe-error', status=RunStatus.FAILED)

    def fake_dispatch(*_args, **_kwargs):
        return ExecutionResult(
            status='failed',
            output_payload={'summary': 'nope', 'path': '/tmp/secret.txt'},
            error_message='Authorization: Bearer secret-token /tmp/secret.txt',
            message='failed',
        )

    monkeypatch.setattr(run_services, 'dispatch_run_execution', fake_dispatch)

    result = run_services.retry_run(run=run)
    result.run.refresh_from_db()

    assert result.run.status == RunStatus.FAILED
    assert result.run.error_message == safe_run_error_message('Authorization: Bearer secret-token /tmp/secret.txt')
    assert REDACTED_VALUE in result.run.error_message
    assert 'secret-token' not in result.run.error_message
    assert '/tmp/secret.txt' not in result.run.error_message
    assert result.run.output_payload == safe_run_output_payload({'summary': 'nope', 'path': '/tmp/secret.txt'})


@pytest.mark.django_db
def test_start_run_exception_path_saves_safe_error_message(monkeypatch: pytest.MonkeyPatch) -> None:
    workflow = Workflow.objects.create(
        name='wf-exception',
        definition_payload={
            'llm': {'enabled': True, 'model': 'test-model'},
            'tools': {'allowed': ['echo']},
        },
    )
    run = Run.objects.create(workflow=workflow, name='run-exception')

    def fake_dispatch(*_args, **_kwargs):
        raise RuntimeError(
            'Traceback (most recent call last):\n'
            '  File "/tmp/secret.txt", line 1, in <module>\n'
            'Authorization: Bearer secret-token /tmp/secret.txt'
        )

    monkeypatch.setattr(run_services, 'dispatch_run_execution', fake_dispatch)

    with pytest.raises(RuntimeError, match='secret-token'):
        run_services.start_run(run=run)

    run.refresh_from_db()
    assert run.status == RunStatus.FAILED
    assert run.error_message == safe_run_error_message(
        RuntimeError(
            'Traceback (most recent call last):\n'
            '  File "/tmp/secret.txt", line 1, in <module>\n'
            'Authorization: Bearer secret-token /tmp/secret.txt'
        )
    )
    assert 'Traceback' not in run.error_message
    assert REDACTED_VALUE in run.error_message
    assert 'secret-token' not in run.error_message
    assert '/tmp/secret.txt' not in run.error_message


@pytest.mark.django_db
def test_resume_run_is_unsupported_and_does_not_dispatch(monkeypatch: pytest.MonkeyPatch) -> None:
    workflow = Workflow.objects.create(name='wf-resume')
    run = Run.objects.create(workflow=workflow, name='run-resume', status=RunStatus.FAILED)
    called = {'value': False}

    def fake_dispatch(*_args, **_kwargs):
        called['value'] = True
        raise AssertionError('dispatch should not be called for resume_run')

    monkeypatch.setattr(run_services, 'dispatch_run_execution', fake_dispatch)

    with pytest.raises(NotImplementedError, match='checkpoint resume'):
        run_services.resume_run(run=run)

    assert called['value'] is False
