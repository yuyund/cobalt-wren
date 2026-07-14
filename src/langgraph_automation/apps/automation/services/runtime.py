"""Runtime factory for the Django control plane.

This module is the dependency assembly boundary for execution-plane services.
It composes concrete dependencies from settings, Workflow, and Run context, but
it does not execute graphs or mutate Run lifecycle state.
"""

from __future__ import annotations

import logging

from langgraph_automation.apps.automation.models.run import Run
from langgraph_automation.apps.automation.services.errors import WorkflowConfigurationError
from langgraph_automation.apps.automation.services.workflow_config import (
    WorkflowConfigIssue,
    parse_workflow_runtime_config,
    validate_workflow_runtime_config,
)
from langgraph_automation.config import settings as app_settings
from langgraph_automation.graphs.runtime import GraphRuntime
from langgraph_automation.integrations.artifact.base import ArtifactStore
from langgraph_automation.integrations.artifact.memory_store import MemoryArtifactStore
from langgraph_automation.integrations.checkpoint.base import CheckpointStore
from langgraph_automation.integrations.checkpoint.memory_store import MemoryCheckpointStore
from langgraph_automation.integrations.llm import LiteLLMClient, ObservedLLMClient
from langgraph_automation.integrations.llm.base import LLMClient
from langgraph_automation.integrations.observability.base import EventSink
from langgraph_automation.integrations.observability.django_event_sink import DjangoEventSink
from langgraph_automation.integrations.observability.types import ObservabilityContext
from langgraph_automation.integrations.tools import (
    AllowlistToolPolicy,
    ECHO_TOOL_NAME,
    EchoTool,
    InMemoryToolRegistry,
    ObservedToolRegistry,
    PolicyAwareToolRegistry,
    ToolPolicyContext,
    ToolRegistry,
)


def build_event_sink(run: Run) -> EventSink:
    """Build the observability sink for a run.

    This is a concrete adapter wiring boundary only; it must not perform business
    logic or runtime execution.
    """

    return DjangoEventSink()


def _format_configuration_issues(issues: tuple[WorkflowConfigIssue, ...]) -> str:
    parts = [f'{issue.path}: {issue.message}' for issue in issues if issue.level == 'error']
    if not parts:
        parts = [f'{issue.path}: {issue.message}' for issue in issues]
    return '; '.join(parts)


def build_llm_client(run: Run, event_sink: EventSink | None = None) -> LLMClient | None:
    """Build the optional LLM client dependency.

    The runtime reads the normalized workflow config, then composes a concrete
    LiteLLMClient wrapped by ObservedLLMClient when LLM is enabled.
    """

    runtime_config = parse_workflow_runtime_config(run.workflow.definition_payload)
    validation = validate_workflow_runtime_config(run.workflow.definition_payload)

    if not runtime_config.llm.enabled:
        return None
    if not runtime_config.llm.model:
        raise WorkflowConfigurationError(_format_configuration_issues(validation.issues) or 'LLM model is required when llm.enabled is true.')

    concrete = LiteLLMClient(
        model=runtime_config.llm.model,
        api_key=app_settings.LLM_API_KEY or None,
        base_url=app_settings.LLM_BASE_URL or None,
        temperature=runtime_config.llm.temperature,
        max_tokens=runtime_config.llm.max_tokens,
    )
    return ObservedLLMClient(
        inner=concrete,
        event_sink=event_sink,
        observability=ObservabilityContext(run_id=run.pk, thread_id=run.thread_id),
    )


def build_tool_registry(run: Run, event_sink: EventSink | None = None) -> ToolRegistry:
    """Build the tool registry dependency stack.

    The production stack currently exposes a single safe toy tool (echo), wrapped
    in policy and observability decorators. Runtime wiring is responsible only for
    composition; tool policy evaluation and observability stay in their own layers.
    """

    concrete = InMemoryToolRegistry()
    concrete.register(ECHO_TOOL_NAME, EchoTool())

    allowed_tools = parse_workflow_runtime_config(run.workflow.definition_payload).tools.allowed_tools
    policy = AllowlistToolPolicy(allowed_tools=frozenset(allowed_tools))
    context = ToolPolicyContext(run_id=run.pk, workflow_id=run.workflow_id, thread_id=run.thread_id)
    policy_registry = PolicyAwareToolRegistry(inner=concrete, policy=policy, context=context)
    return ObservedToolRegistry(
        inner=policy_registry,
        event_sink=event_sink,
        observability=ObservabilityContext(run_id=run.pk, thread_id=run.thread_id),
    )


def build_artifact_store(run: Run, event_sink: EventSink | None = None) -> ArtifactStore:
    """Build the artifact store dependency.

    The current artifact store is in-memory only. It does not persist artifact
    bodies and does not use ARTIFACT_ROOT yet.
    """

    del run, event_sink
    return MemoryArtifactStore()


def build_checkpoint_store(run: Run, event_sink: EventSink | None = None) -> CheckpointStore:
    """Build the checkpoint store dependency."""

    del run, event_sink
    return MemoryCheckpointStore()


def build_graph_runtime(run: Run) -> GraphRuntime:
    """Build the execution-plane dependency bundle for a run.

    This function reads configuration and assembles concrete dependencies only.
    It must not execute graphs, update Run lifecycle state, or contain workflow
    business logic.
    """

    event_sink = build_event_sink(run)
    return GraphRuntime(
        logger=logging.getLogger(f'langgraph_automation.run.{run.pk}'),
        observability=ObservabilityContext(run_id=run.pk, thread_id=run.thread_id),
        event_sink=event_sink,
        llm_client=build_llm_client(run, event_sink),
        tool_registry=build_tool_registry(run, event_sink),
        artifact_store=build_artifact_store(run, event_sink),
        checkpoint_store=build_checkpoint_store(run, event_sink),
    )
