"""Run service safety and resume semantics tests."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from langgraph_automation.apps.automation.models.run import Run, RunStatus
from langgraph_automation.apps.automation.models.workflow import Workflow
from langgraph_automation.apps.automation.services import runs as run_services
from langgraph_automation.apps.automation.services import runtime as runtime_module
from langgraph_automation.core.redaction import REDACTED_VALUE
from langgraph_automation.core.result_safety import safe_run_error_message, safe_run_output_payload
from langgraph_automation.config.normalizer import load_normalized_package_config_from_mapping
from langgraph_automation.graphs.runner import ExecutionResult
from tests.support.recording_event_sink import RecordingEventSink


class _FakeRuntimeFactory:
    def __init__(self, package_config: object) -> None:
        self.package_config = package_config
        self.calls: list[object] = []

    def build_graph_runtime(self, run_arg: object) -> object:
        self.calls.append(run_arg)
        return SimpleNamespace(event_sink=None)


def _run_execution_services(package_config: object) -> object:
    return run_services.runtime_module.RunExecutionServices(
        runtime_factory=_FakeRuntimeFactory(package_config)
    )


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
    package_settings = load_normalized_package_config_from_mapping({"version": 1})
    services = _run_execution_services(package_settings)

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

    result = run_services.start_run(run=run, services=services)
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
def test_start_run_uses_bound_package_config_once(monkeypatch: pytest.MonkeyPatch) -> None:
    workflow = Workflow.objects.create(
        name='wf-package-settings',
        definition_payload={
            'llm': {'enabled': True, 'model': 'test-model'},
            'tools': {'allowed': ['echo']},
        },
    )
    run = Run.objects.create(workflow=workflow, name='run-package-settings')
    package_settings = load_normalized_package_config_from_mapping({"version": 1})
    factory = _FakeRuntimeFactory(package_settings)
    services = run_services.runtime_module.RunExecutionServices(runtime_factory=factory)

    def fake_dispatch_run_execution(*_args, **_kwargs):
        return ExecutionResult(status=RunStatus.SUCCEEDED, output_payload={}, message='ok')

    monkeypatch.setattr(run_services, 'dispatch_run_execution', fake_dispatch_run_execution)

    result = run_services.start_run(run=run, services=services)

    assert result.run.status == RunStatus.SUCCEEDED
    assert factory.package_config is package_settings
    assert factory.calls == [run]


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
    package_settings = load_normalized_package_config_from_mapping({"version": 1})
    services = _run_execution_services(package_settings)

    def fake_dispatch(*_args, **_kwargs):
        return ExecutionResult(
            status='failed',
            output_payload={'summary': 'nope', 'path': '/tmp/secret.txt'},
            error_message='Authorization: Bearer secret-token /tmp/secret.txt',
            message='failed',
        )

    monkeypatch.setattr(run_services, 'dispatch_run_execution', fake_dispatch)

    result = run_services.retry_run(run=run, services=services)
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
    package_settings = load_normalized_package_config_from_mapping({"version": 1})
    services = _run_execution_services(package_settings)

    def fake_dispatch(*_args, **_kwargs):
        raise RuntimeError(
            'Traceback (most recent call last):\n'
            '  File "/tmp/secret.txt", line 1, in <module>\n'
            'Authorization: Bearer secret-token /tmp/secret.txt'
        )

    monkeypatch.setattr(run_services, 'dispatch_run_execution', fake_dispatch)

    with pytest.raises(RuntimeError, match='secret-token'):
        run_services.start_run(run=run, services=services)

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


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("action_name", "initial_status"),
    [
        ("start_run", RunStatus.PENDING),
        ("retry_run", RunStatus.FAILED),
    ],
)
def test_physical_persistence_configuration_is_rejected_before_runtime_and_persistence_side_effects(
    action_name: str,
    initial_status: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workflow = Workflow.objects.create(
        name=f'wf-invalid-physical-config-{action_name}',
        definition_payload={
            'llm': {'enabled': True, 'model': 'test-model'},
            'tools': {'allowed': ['echo']},
            'stores': {
                'artifact': {'backend': 'filesystem', 'config': {'root': '/tmp/artifacts'}},
                'checkpoint': {'backend': 'filesystem', 'config': {'root': '/tmp/checkpoints'}},
            },
        },
    )
    run = Run.objects.create(workflow=workflow, name=f'run-invalid-physical-config-{action_name}', status=initial_status)
    services = runtime_module.build_run_execution_services_from_mapping({'version': 1})
    sink = RecordingEventSink()
    artifact_builder_called = False
    checkpoint_builder_called = False
    dispatch_called = False

    def fake_event_sink(_run: Run) -> RecordingEventSink:
        return sink

    def fail_artifact_builder(*_args, **_kwargs):
        nonlocal artifact_builder_called
        artifact_builder_called = True
        raise AssertionError('artifact builder should not be called for invalid workflow physical config')

    def fail_checkpoint_builder(*_args, **_kwargs):
        nonlocal checkpoint_builder_called
        checkpoint_builder_called = True
        raise AssertionError('checkpoint builder should not be called for invalid workflow physical config')

    def fail_dispatch(*_args, **_kwargs):
        nonlocal dispatch_called
        dispatch_called = True
        raise AssertionError('dispatch should not be called for invalid workflow physical config')

    monkeypatch.setattr(runtime_module, 'build_event_sink', fake_event_sink)
    monkeypatch.setattr(runtime_module, 'build_package_artifact_store', fail_artifact_builder)
    monkeypatch.setattr(runtime_module, 'build_package_checkpoint_store', fail_checkpoint_builder)
    monkeypatch.setattr(run_services, 'dispatch_run_execution', fail_dispatch)

    action = getattr(run_services, action_name)
    result = action(run=run, services=services)
    run.refresh_from_db()

    assert result.run.status == RunStatus.FAILED
    assert run.status == RunStatus.FAILED
    assert run.started_at is not None
    assert run.finished_at is not None
    assert run.error_message.startswith('WorkflowConfigurationError:')
    assert '/tmp/artifacts' not in run.error_message
    assert '/tmp/checkpoints' not in run.error_message
    assert artifact_builder_called is False
    assert checkpoint_builder_called is False
    assert dispatch_called is False
    assert [event.kind for event in sink.run_events] == ['run.failed']
    assert all(event.kind != 'run.started' for event in sink.run_events)
