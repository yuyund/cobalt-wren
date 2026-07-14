"""Runtime factory tests."""

from __future__ import annotations

import logging

import pytest

from langgraph_automation.apps.automation.models.run import Run
from langgraph_automation.apps.automation.models.workflow import Workflow
from langgraph_automation.apps.automation.services.errors import WorkflowConfigurationError
from langgraph_automation.apps.automation.services.runtime import (
    build_artifact_store,
    build_checkpoint_store,
    build_graph_runtime,
    build_llm_client,
    build_tool_registry,
)
from langgraph_automation.apps.automation.services.workflow_config import MINIMAL_GRAPH_KIND
from langgraph_automation.config import settings as app_settings
from langgraph_automation.core.errors import MissingRuntimeDependencyError
from langgraph_automation.graphs.runtime import GraphRuntime
from langgraph_automation.integrations.artifact.memory_store import MemoryArtifactStore
from langgraph_automation.integrations.checkpoint.memory_store import MemoryCheckpointStore
from langgraph_automation.integrations.llm import LiteLLMClient, ObservedLLMClient
from langgraph_automation.integrations.observability.types import ObservabilityContext, SpanRef
from langgraph_automation.integrations.tools.policy import POLICY_DENIED_EXIT_CODE
from tests.support.recording_event_sink import RecordingEventSink


@pytest.mark.django_db
def test_build_graph_runtime_returns_execution_bundle() -> None:
    workflow = Workflow.objects.create(name='wf-runtime', definition_payload={'tools': {'allowed': ['echo']}})
    run = Run.objects.create(workflow=workflow, name='run-runtime')

    runtime = build_graph_runtime(run)

    assert runtime.event_sink is not None
    assert runtime.llm_client is None
    assert runtime.tool_registry is not None
    assert isinstance(runtime.artifact_store, MemoryArtifactStore)
    assert isinstance(runtime.checkpoint_store, MemoryCheckpointStore)
    assert runtime.workflow_config.graph.kind == MINIMAL_GRAPH_KIND
    assert runtime.observability.run_id == run.pk
    assert runtime.observability.thread_id == ''
    assert runtime.require_tool_registry() is runtime.tool_registry
    assert build_llm_client(run, runtime.event_sink) is None
    assert build_tool_registry(run, runtime.event_sink) is not None
    assert isinstance(build_artifact_store(run, runtime.event_sink), MemoryArtifactStore)
    assert isinstance(build_checkpoint_store(run, runtime.event_sink), MemoryCheckpointStore)


@pytest.mark.django_db
def test_build_graph_runtime_rejects_unknown_graph_kind() -> None:
    workflow = Workflow.objects.create(
        name='wf-runtime-unknown-graph',
        definition_payload={
            'graph': {'kind': 'unknown-kind'},
            'llm': {'enabled': True, 'model': 'gpt-4o-mini'},
            'tools': {'allowed': ['echo']},
        },
    )
    run = Run.objects.create(workflow=workflow, name='run-runtime-unknown-graph')

    with pytest.raises(WorkflowConfigurationError, match='Unsupported graph kind'):
        build_graph_runtime(run)


@pytest.mark.django_db
def test_build_tool_registry_allows_echo_when_configured() -> None:
    workflow = Workflow.objects.create(name='wf-tool-allowed', definition_payload={'tools': {'allowed': ['echo']}})
    run = Run.objects.create(workflow=workflow, name='run-tool-allowed', thread_id='thread-1')
    sink = RecordingEventSink()

    registry = build_tool_registry(run, sink)
    result = registry.run('echo', text='Authorization: Bearer secret-token /tmp/secret.txt')

    assert result.exit_code == 0
    assert result.metadata['tool_name'] == 'echo'
    assert len(result.output_summary) <= 300
    assert 'secret-token' not in result.output_summary
    assert '/tmp/secret.txt' not in result.output_summary
    assert result.output == result.output_summary
    assert sink.spans['span-1'].status == 'succeeded'


@pytest.mark.django_db
def test_build_tool_registry_defaults_to_deny_without_allowed_tools() -> None:
    workflow = Workflow.objects.create(name='wf-tool-denied')
    run = Run.objects.create(
        workflow=workflow,
        name='run-tool-denied',
        thread_id='thread-1',
        input_payload={'tools': {'allowed': ['echo']}},
    )
    sink = RecordingEventSink()

    registry = build_tool_registry(run, sink)
    result = registry.run('echo', text='hello')

    assert result.exit_code == POLICY_DENIED_EXIT_CODE
    assert result.metadata['policy_denied'] is True
    assert result.metadata['tool_name'] == 'echo'
    assert sink.spans['span-1'].status == 'failed'


@pytest.mark.django_db
def test_build_llm_client_returns_none_when_disabled_or_missing_config() -> None:
    workflow = Workflow.objects.create(name='wf-llm-disabled')
    run = Run.objects.create(workflow=workflow, name='run-llm-disabled')

    assert build_llm_client(run, None) is None

    workflow_enabled_missing = Workflow.objects.create(name='wf-llm-missing', definition_payload={'llm': {'enabled': True}})
    run_enabled_missing = Run.objects.create(workflow=workflow_enabled_missing, name='run-llm-missing')

    with pytest.raises(WorkflowConfigurationError):
        build_llm_client(run_enabled_missing, None)


@pytest.mark.django_db
def test_build_llm_client_builds_observed_lite_llm_client_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app_settings, 'LLM_API_KEY', 'settings-api-key', raising=False)
    monkeypatch.setattr(app_settings, 'LLM_BASE_URL', 'https://llm.example.invalid', raising=False)

    workflow = Workflow.objects.create(
        name='wf-llm-enabled',
        definition_payload={
            'llm': {
                'enabled': True,
                'model': 'gpt-4o-mini',
                'temperature': 0.25,
                'max_tokens': 256,
            },
        },
    )
    run = Run.objects.create(
        workflow=workflow,
        name='run-llm-enabled',
        input_payload={
            'llm': {
                'model': 'ignored-model',
                'api_key': 'ignored-secret',
                'base_url': 'https://ignored.example.invalid',
            },
        },
    )
    sink = RecordingEventSink()

    client = build_llm_client(run, sink)
    runtime = build_graph_runtime(run)

    assert isinstance(client, ObservedLLMClient)
    assert isinstance(client.inner, LiteLLMClient)
    assert client.inner.model == 'gpt-4o-mini'
    assert client.inner.api_key == 'settings-api-key'
    assert client.inner.base_url == 'https://llm.example.invalid'
    assert client.inner.temperature == 0.25
    assert client.inner.max_tokens == 256
    assert isinstance(runtime.llm_client, ObservedLLMClient)
    assert isinstance(runtime.llm_client.inner, LiteLLMClient)
    assert runtime.llm_client.inner.model == 'gpt-4o-mini'
    assert runtime.tool_registry is not None


def test_graph_runtime_requires_optional_dependencies_fail_fast() -> None:
    runtime = GraphRuntime(logger=logging.getLogger('test-runtime'))

    with pytest.raises(MissingRuntimeDependencyError):
        runtime.require_llm_client()

    with pytest.raises(MissingRuntimeDependencyError):
        runtime.require_tool_registry()


def test_with_parent_span_preserves_optional_dependencies() -> None:
    runtime = GraphRuntime(
        logger=logging.getLogger('test-runtime-parent'),
        observability=ObservabilityContext(run_id=1, thread_id='thread-1'),
    )

    updated = runtime.with_parent_span(SpanRef('span-1'), node_name='planner')

    assert updated is not runtime
    assert updated.observability.parent_span == SpanRef('span-1')
    assert updated.observability.node_name == 'planner'
    assert updated.llm_client is None
    assert updated.tool_registry is None
    assert runtime.observability.parent_span is None
    assert runtime.observability.node_name == ''
