"""Runtime factory for the Django control plane.

This module is the dependency assembly boundary for execution-plane services.
It composes concrete dependencies from trusted package settings, workflow
configuration, and run context, but it does not execute graphs or mutate Run
lifecycle state.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass

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
from langgraph_automation.config.normalizer import load_normalized_package_config_from_mapping
from langgraph_automation.config.models import NormalizedPackageConfig, StoreBackendConfig
from langgraph_automation.graphs.config import (
    GraphRuntimeConfig,
    GraphRuntimeGraphConfig,
    GraphRuntimeLLMConfig,
    GraphRuntimeToolConfig,
)
from langgraph_automation.graphs.registry import GraphRegistry, default_graph_kind
from langgraph_automation.graphs.runtime import GraphRuntime
from langgraph_automation.integrations.artifact.base import ArtifactStore
from langgraph_automation.integrations.checkpoint.base import CheckpointStore
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


@dataclass(frozen=True, slots=True)
class ApplicationRuntimeFactory:
    """Bind normalized package config once for application composition."""

    package_config: NormalizedPackageConfig

    def build_graph_runtime(self, run: Run) -> GraphRuntime:
        return build_graph_runtime(run, package_settings=self.package_config)


@dataclass(frozen=True, slots=True)
class RunExecutionServices:
    """Bound execution services for run lifecycle orchestration."""

    runtime_factory: ApplicationRuntimeFactory

    def build_graph_runtime(self, run: Run) -> GraphRuntime:
        return self.runtime_factory.build_graph_runtime(run)


def get_run_execution_services() -> RunExecutionServices:
    """Return the app-config bound run execution services instance."""

    from django.apps import apps as django_apps

    app_config = django_apps.get_app_config("automation")
    services = getattr(app_config, "run_execution_services", None)
    if services is None:
        raise RuntimeError("automation app runtime services have not been initialized")
    return services


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


def _reserved_physical_persistence_issues(definition_payload: object) -> tuple[WorkflowConfigIssue, ...]:
    if not isinstance(definition_payload, dict):
        return ()

    issues: list[WorkflowConfigIssue] = []
    stores = definition_payload.get("stores")
    if not isinstance(stores, dict):
        return ()

    for store_name, issue_path, issue_code, issue_message in (
        (
            "artifact",
            "stores.artifact",
            "reserved_artifact_store_config",
            "Workflow definition payload must not declare artifact store backend configuration.",
        ),
        (
            "checkpoint",
            "stores.checkpoint",
            "reserved_checkpoint_store_config",
            "Workflow definition payload must not declare checkpoint store backend configuration.",
        ),
    ):
        store_config = stores.get(store_name)
        if not isinstance(store_config, dict):
            continue
        if any(key in store_config for key in {"backend", "config", "root"}):
            issues.append(
                WorkflowConfigIssue(
                    path=issue_path,
                    code=issue_code,
                    message=issue_message,
                    level="error",
                )
            )

    return tuple(issues)


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
    reserved = _reserved_physical_persistence_issues(run.workflow.definition_payload)
    return runtime_config, (*validation.issues, *reserved)


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


def _default_package_settings() -> NormalizedPackageConfig:
    return load_normalized_package_config_from_mapping({"version": 1})


def build_application_runtime_factory(package_config: NormalizedPackageConfig) -> ApplicationRuntimeFactory:
    """Bind normalized package config to the application runtime composition owner."""

    return ApplicationRuntimeFactory(package_config=package_config)


def build_run_execution_services(package_config: NormalizedPackageConfig) -> RunExecutionServices:
    """Build run execution services from normalized package config."""

    return RunExecutionServices(runtime_factory=build_application_runtime_factory(package_config))


def build_run_execution_services_from_mapping(config: Mapping[str, object]) -> RunExecutionServices:
    """Normalize trusted raw package config once and bind it to execution services."""

    return build_run_execution_services(load_normalized_package_config_from_mapping(config))


def _artifact_store_settings(package_settings: NormalizedPackageConfig | None) -> StoreBackendConfig | None:
    settings = package_settings or _default_package_settings()
    return settings.stores.get("artifact")


def build_artifact_store(
    run: Run,
    event_sink: EventSink | None = None,
    *,
    package_settings: NormalizedPackageConfig | None = None,
) -> ArtifactStore:
    """Build the artifact store dependency.

    The store is selected from trusted package settings and then constructed
    through the canonical runtime builder so the chosen instance reaches the
    execution owner unchanged.
    """

    del event_sink
    del run
    settings = normalize_artifact_store_settings(_artifact_store_settings(package_settings))
    return build_package_artifact_store(settings)


def build_checkpoint_store(
    run: Run,
    event_sink: EventSink | None = None,
    *,
    package_settings: NormalizedPackageConfig | None = None,
) -> CheckpointStore:
    """Build the checkpoint store dependency for a run.

    The store is selected from trusted package settings and then constructed
    through the canonical runtime builder so the chosen instance reaches the
    execution owner unchanged.
    """

    del event_sink
    del run
    settings = (package_settings or _default_package_settings()).checkpoint_store
    return build_package_checkpoint_store(settings)


def build_graph_runtime(
    run: Run,
    *,
    package_settings: NormalizedPackageConfig | None = None,
) -> GraphRuntime:
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
        artifact_store=build_artifact_store(run, event_sink, package_settings=package_settings),
        checkpoint_store=build_checkpoint_store(run, event_sink, package_settings=package_settings),
    )
