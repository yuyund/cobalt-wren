"""Runtime factory for the Django control plane.

This module is the dependency assembly boundary for execution-plane services.
It composes concrete dependencies from settings, Workflow, and Run context, but
it does not execute graphs or mutate Run lifecycle state.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping

from langgraph_automation.apps.automation.models.run import Run
from langgraph_automation.apps.automation.services.errors import WorkflowConfigurationError
from langgraph_automation.apps.automation.services.workflow_config import (
    WorkflowConfigIssue,
    WorkflowRuntimeConfig,
    parse_workflow_runtime_config,
    validate_workflow_runtime_config,
)
from langgraph_automation.config import settings as app_settings
from langgraph_automation.config.artifact_store import normalize_artifact_store_settings
from langgraph_automation.config.checkpoint_store import normalize_checkpoint_store_settings
from langgraph_automation.config.models import StoreBackendConfig
from langgraph_automation.graphs.config import (
    GraphRuntimeConfig,
    GraphRuntimeGraphConfig,
    GraphRuntimeLLMConfig,
    GraphRuntimeToolConfig,
)
from langgraph_automation.graphs.registry import GraphRegistry, default_graph_kind
from langgraph_automation.graphs.runtime import GraphRuntime
from langgraph_automation.integrations.artifact.base import ArtifactStore
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
from langgraph_automation.workflows.catalog import build_builtin_graph_registry

from langgraph_automation.runtime.artifact_store import build_artifact_store as build_package_artifact_store
from langgraph_automation.runtime.checkpoint_store import build_checkpoint_store as build_package_checkpoint_store


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


def _runtime_config(run: Run) -> WorkflowRuntimeConfig:
    return parse_workflow_runtime_config(run.workflow.definition_payload, default_graph_kind=default_graph_kind())


def _store_backend_config(definition_payload: Mapping[str, object] | None, store_name: str) -> StoreBackendConfig | None:
    if not isinstance(definition_payload, Mapping):
        return None
    stores = definition_payload.get("stores")
    if stores is None:
        return None
    if not isinstance(stores, Mapping):
        raise WorkflowConfigurationError("Workflow store configuration must be a mapping.")
    raw_store_config = stores.get(store_name)
    if raw_store_config is None:
        return None
    if not isinstance(raw_store_config, Mapping):
        raise WorkflowConfigurationError(f"Workflow {store_name} store configuration must be a mapping.")

    backend = raw_store_config.get("backend")
    if not isinstance(backend, str) or not backend.strip():
        raise WorkflowConfigurationError(f"Workflow {store_name} store backend is invalid.")
    config = raw_store_config.get("config", {})
    if config is None:
        config = {}
    if not isinstance(config, Mapping):
        raise WorkflowConfigurationError(f"Workflow {store_name} store config must be a mapping.")
    metadata = raw_store_config.get("metadata", {})
    if metadata is None:
        metadata = {}
    if not isinstance(metadata, Mapping):
        raise WorkflowConfigurationError(f"Workflow {store_name} store metadata must be a mapping.")

    return StoreBackendConfig(backend=backend, config=config, metadata=metadata)


def _to_graph_runtime_config(workflow_config: WorkflowRuntimeConfig) -> GraphRuntimeConfig:
    return GraphRuntimeConfig(
        graph=GraphRuntimeGraphConfig(kind=workflow_config.graph.kind),
        llm=GraphRuntimeLLMConfig(
            enabled=workflow_config.llm.enabled,
            model=workflow_config.llm.model,
            temperature=workflow_config.llm.temperature,
            max_tokens=workflow_config.llm.max_tokens,
        ),
        tools=GraphRuntimeToolConfig(allowed_tools=workflow_config.tools.allowed_tools),
    )


def _validate_runtime_config(run: Run, graph_registry: GraphRegistry) -> tuple[WorkflowRuntimeConfig, tuple[WorkflowConfigIssue, ...]]:
    runtime_config = _runtime_config(run)
    validation = validate_workflow_runtime_config(
        run.workflow.definition_payload,
        default_graph_kind=default_graph_kind(),
        supported_graph_kinds=graph_registry.supported_graph_kinds(),
        graph_requirements=graph_registry.graph_requirements(),
    )
    return runtime_config, validation.issues


def build_llm_client(
    run: Run,
    event_sink: EventSink | None = None,
    runtime_config: WorkflowRuntimeConfig | None = None,
) -> LLMClient | None:
    """Build the optional LLM client dependency.

    The runtime reads the normalized workflow config, then composes a concrete
    LiteLLMClient wrapped by ObservedLLMClient when LLM is enabled.
    """

    runtime_config = runtime_config or _runtime_config(run)
    if not runtime_config.llm.enabled:
        return None
    if not runtime_config.llm.model:
        raise WorkflowConfigurationError('LLM model is required when llm.enabled is true.')

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


def build_tool_registry(
    run: Run,
    event_sink: EventSink | None = None,
    runtime_config: WorkflowRuntimeConfig | None = None,
) -> ToolRegistry:
    """Build the tool registry dependency stack.

    The production stack currently exposes a single safe toy tool (echo), wrapped
    in policy and observability decorators. Runtime wiring is responsible only for
    composition; tool policy evaluation and observability stay in their own layers.
    """

    runtime_config = runtime_config or _runtime_config(run)
    concrete = InMemoryToolRegistry()
    concrete.register(ECHO_TOOL_NAME, EchoTool())

    policy = AllowlistToolPolicy(allowed_tools=frozenset(runtime_config.tools.allowed_tools))
    context = ToolPolicyContext(run_id=run.pk, workflow_id=run.workflow_id, thread_id=run.thread_id)
    policy_registry = PolicyAwareToolRegistry(inner=concrete, policy=policy, context=context)
    return ObservedToolRegistry(
        inner=policy_registry,
        event_sink=event_sink,
        observability=ObservabilityContext(run_id=run.pk, thread_id=run.thread_id),
    )


def build_artifact_store(run: Run, event_sink: EventSink | None = None) -> ArtifactStore:
    """Build the artifact store dependency.

    The store is selected from the workflow payload and then constructed through
    the canonical runtime builder so the chosen instance reaches the execution
    owner unchanged.
    """

    del event_sink
    settings = normalize_artifact_store_settings(_store_backend_config(run.workflow.definition_payload, "artifact"))
    return build_package_artifact_store(settings)


def build_checkpoint_store(run: Run, event_sink: EventSink | None = None) -> object:
    """Build the checkpoint store dependency for a run.

    The store is selected from the workflow payload and then constructed through
    the canonical runtime builder so the chosen instance reaches the execution
    owner unchanged.
    """

    del event_sink
    settings = normalize_checkpoint_store_settings(_store_backend_config(run.workflow.definition_payload, "checkpoint"))
    return build_package_checkpoint_store(settings)


def build_graph_runtime(run: Run) -> GraphRuntime:
    """Build the execution-plane dependency bundle for a run.

    This function reads configuration and assembles concrete dependencies only.
    It must not execute graphs, update Run lifecycle state, or contain workflow
    business logic.
    """

    graph_registry = build_builtin_graph_registry()
    runtime_config, issues = _validate_runtime_config(run, graph_registry)
    validation = tuple(issue for issue in issues if issue.level == 'error')
    if validation:
        raise WorkflowConfigurationError(_format_configuration_issues(tuple(validation)))

    event_sink = build_event_sink(run)
    return GraphRuntime(
        logger=logging.getLogger(f'langgraph_automation.run.{run.pk}'),
        observability=ObservabilityContext(run_id=run.pk, thread_id=run.thread_id),
        workflow_config=_to_graph_runtime_config(runtime_config),
        graph_registry=graph_registry,
        event_sink=event_sink,
        llm_client=build_llm_client(run, event_sink, runtime_config),
        tool_registry=build_tool_registry(run, event_sink, runtime_config),
        artifact_store=build_artifact_store(run, event_sink),
        checkpoint_store=build_checkpoint_store(run, event_sink),
    )
