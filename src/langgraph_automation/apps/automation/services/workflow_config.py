"""Workflow runtime config parsing and validation helpers."""

from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

from langgraph_automation.core.summary import summarize_mapping

MINIMAL_GRAPH_KIND = 'llm_echo_summary'


class _GraphRuntimeRequirements(Protocol):
    requires_llm: bool
    required_tools: tuple[str, ...]


@dataclass(frozen=True)
class GraphWorkflowConfig:
    """Normalized workflow-level graph configuration."""

    kind: str = MINIMAL_GRAPH_KIND


@dataclass(frozen=True)
class LLMWorkflowConfig:
    """Normalized workflow-level LLM configuration."""

    enabled: bool = False
    model: str = ''
    temperature: float | None = None
    max_tokens: int | None = None


@dataclass(frozen=True)
class ToolWorkflowConfig:
    """Normalized workflow-level tool policy configuration."""

    allowed_tools: tuple[str, ...] = ()


@dataclass(frozen=True)
class WorkflowRuntimeConfig:
    """Normalized runtime configuration extracted from Workflow.definition_payload."""

    graph: GraphWorkflowConfig = field(default_factory=GraphWorkflowConfig)
    llm: LLMWorkflowConfig = field(default_factory=LLMWorkflowConfig)
    tools: ToolWorkflowConfig = field(default_factory=ToolWorkflowConfig)


@dataclass(frozen=True)
class WorkflowConfigIssue:
    path: str
    code: str
    message: str
    level: str = 'error'


@dataclass(frozen=True)
class WorkflowConfigValidation:
    issues: tuple[WorkflowConfigIssue, ...] = ()

    @property
    def has_errors(self) -> bool:
        return any(issue.level == 'error' for issue in self.issues)


def _is_numeric_value(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _extract_allowed_tool_names(definition_payload: Mapping[str, Any] | None) -> tuple[str, ...]:
    if not isinstance(definition_payload, Mapping):
        return ()
    tools = definition_payload.get('tools')
    if not isinstance(tools, Mapping):
        return ()
    allowed = tools.get('allowed')
    if not isinstance(allowed, list):
        return ()

    ordered_unique: list[str] = []
    seen: set[str] = set()
    for entry in allowed:
        if not isinstance(entry, str):
            continue
        name = entry.strip()
        if not name or name in seen:
            continue
        seen.add(name)
        ordered_unique.append(name)
    return tuple(ordered_unique)


def extract_allowed_tool_names(definition_payload: Mapping[str, Any] | None) -> tuple[str, ...]:
    """Backward-compatible helper for tool allowlist extraction."""

    return _extract_allowed_tool_names(definition_payload)


def _parse_graph_config(definition_payload: Mapping[str, Any] | None, *, default_graph_kind: str) -> GraphWorkflowConfig:
    if not isinstance(definition_payload, Mapping):
        return GraphWorkflowConfig(kind=default_graph_kind)
    graph = definition_payload.get('graph')
    if not isinstance(graph, Mapping):
        return GraphWorkflowConfig(kind=default_graph_kind)

    kind_value = graph.get('kind', default_graph_kind)
    if not isinstance(kind_value, str):
        return GraphWorkflowConfig(kind=default_graph_kind)
    kind = kind_value.strip() or default_graph_kind
    return GraphWorkflowConfig(kind=kind)


def parse_workflow_runtime_config(
    definition_payload: Mapping[str, Any] | None,
    *,
    default_graph_kind: str = MINIMAL_GRAPH_KIND,
) -> WorkflowRuntimeConfig:
    """Parse a workflow definition payload into normalized runtime config."""

    return WorkflowRuntimeConfig(
        graph=_parse_graph_config(definition_payload, default_graph_kind=default_graph_kind),
        llm=_parse_llm_config(definition_payload),
        tools=ToolWorkflowConfig(allowed_tools=_extract_allowed_tool_names(definition_payload)),
    )


def _parse_llm_config(definition_payload: Mapping[str, Any] | None) -> LLMWorkflowConfig:
    if not isinstance(definition_payload, Mapping):
        return LLMWorkflowConfig()
    llm = definition_payload.get('llm')
    if not isinstance(llm, Mapping):
        return LLMWorkflowConfig()

    enabled_value = llm.get('enabled', False)
    enabled = enabled_value is True
    model_value = llm.get('model', '')
    model = model_value if isinstance(model_value, str) else ''
    model = model.strip()
    temperature_value = llm.get('temperature')
    temperature = float(temperature_value) if _is_numeric_value(temperature_value) else None
    max_tokens_value = llm.get('max_tokens')
    max_tokens = max_tokens_value if _is_positive_int(max_tokens_value) else None
    return LLMWorkflowConfig(enabled=enabled, model=model, temperature=temperature, max_tokens=max_tokens)


def _graph_kind_issue_message(
    default_graph_kind: str,
    *,
    missing: bool = False,
    empty: bool = False,
    invalid_type: bool = False,
) -> str:
    if missing:
        return f'graph.kind is missing; defaulting to {default_graph_kind}.'
    if empty:
        return f'graph.kind is empty; defaulting to {default_graph_kind}.'
    if invalid_type:
        return f'graph.kind must be a string; defaulting to {default_graph_kind}.'
    return f'graph.kind is invalid; defaulting to {default_graph_kind}.'


def validate_workflow_runtime_config(
    definition_payload: Mapping[str, Any] | None,
    *,
    default_graph_kind: str = MINIMAL_GRAPH_KIND,
    supported_graph_kinds: Collection[str] | None = None,
    graph_requirements: Mapping[str, _GraphRuntimeRequirements] | None = None,
) -> WorkflowConfigValidation:
    """Validate workflow runtime configuration and return normalized issues."""

    issues: list[WorkflowConfigIssue] = []
    effective_graph_kind = default_graph_kind
    llm_enabled = False

    if not isinstance(definition_payload, Mapping):
        issues.append(
            WorkflowConfigIssue(
                path='definition_payload',
                code='invalid_mapping',
                message='Workflow definition payload must be a mapping.',
                level='warning',
            )
        )
        return WorkflowConfigValidation(issues=tuple(issues))

    graph = definition_payload.get('graph')
    if graph is None:
        issues.append(
            WorkflowConfigIssue(
                path='graph.kind',
                code='missing_graph_kind',
                message=_graph_kind_issue_message(default_graph_kind, missing=True),
                level='warning',
            )
        )
    elif not isinstance(graph, Mapping):
        issues.append(
            WorkflowConfigIssue(
                path='graph',
                code='invalid_graph_type',
                message='Graph configuration must be a mapping.',
                level='warning',
            )
        )
    else:
        kind = graph.get('kind')
        if kind is None:
            issues.append(
                WorkflowConfigIssue(
                    path='graph.kind',
                    code='missing_graph_kind',
                    message=_graph_kind_issue_message(default_graph_kind, missing=True),
                    level='warning',
                )
            )
        elif not isinstance(kind, str):
            issues.append(
                WorkflowConfigIssue(
                    path='graph.kind',
                    code='invalid_graph_kind_type',
                    message=_graph_kind_issue_message(default_graph_kind, invalid_type=True),
                    level='warning',
                )
            )
        else:
            normalized_kind = kind.strip()
            if not normalized_kind:
                issues.append(
                    WorkflowConfigIssue(
                        path='graph.kind',
                        code='empty_graph_kind',
                        message=_graph_kind_issue_message(default_graph_kind, empty=True),
                        level='warning',
                    )
                )
            else:
                effective_graph_kind = normalized_kind

    llm_section = definition_payload.get('llm')
    if llm_section is None:
        issues.append(
            WorkflowConfigIssue(
                path='llm',
                code='missing_llm',
                message='LLM configuration is missing.',
                level='warning',
            )
        )
    elif not isinstance(llm_section, Mapping):
        issues.append(
            WorkflowConfigIssue(
                path='llm',
                code='invalid_llm_type',
                message='LLM configuration must be a mapping.',
                level='warning',
            )
        )
    else:
        enabled_value = llm_section.get('enabled', False)
        llm_enabled = enabled_value is True
        if not isinstance(enabled_value, bool):
            issues.append(
                WorkflowConfigIssue(
                    path='llm.enabled',
                    code='invalid_llm_enabled_type',
                    message='LLM enabled flag must be a boolean.',
                    level='error',
                )
            )
        if llm_enabled:
            model = llm_section.get('model')
            if not isinstance(model, str) or not model.strip():
                issues.append(
                    WorkflowConfigIssue(
                        path='llm.model',
                        code='missing_llm_model',
                        message='LLM model is required when LLM is enabled.',
                        level='error',
                    )
                )
        temperature = llm_section.get('temperature')
        if temperature is not None and not _is_numeric_value(temperature):
            issues.append(
                WorkflowConfigIssue(
                    path='llm.temperature',
                    code='invalid_llm_temperature',
                    message='LLM temperature must be numeric.',
                    level='warning',
                )
            )
        max_tokens = llm_section.get('max_tokens')
        if max_tokens is not None and not _is_positive_int(max_tokens):
            issues.append(
                WorkflowConfigIssue(
                    path='llm.max_tokens',
                    code='invalid_llm_max_tokens',
                    message='LLM max_tokens must be a positive integer.',
                    level='warning',
                )
            )

    tools_section = definition_payload.get('tools')
    if tools_section is None:
        issues.append(
            WorkflowConfigIssue(
                path='tools.allowed',
                code='missing_tools_allowed',
                message='Allowed tool list is missing.',
                level='warning',
            )
        )
    elif not isinstance(tools_section, Mapping):
        issues.append(
            WorkflowConfigIssue(
                path='tools',
                code='invalid_tools_type',
                message='Tool configuration must be a mapping.',
                level='warning',
            )
        )
    else:
        allowed = tools_section.get('allowed')
        if allowed is None:
            issues.append(
                WorkflowConfigIssue(
                    path='tools.allowed',
                    code='missing_tools_allowed',
                    message='Allowed tool list is missing.',
                    level='warning',
                )
            )
        elif not isinstance(allowed, list):
            issues.append(
                WorkflowConfigIssue(
                    path='tools.allowed',
                    code='invalid_tools_allowed_type',
                    message='Allowed tool list must be a list.',
                    level='warning',
                )
            )
        else:
            invalid_items = [entry for entry in allowed if not isinstance(entry, str) or not entry.strip()]
            if invalid_items:
                issues.append(
                    WorkflowConfigIssue(
                        path='tools.allowed',
                        code='invalid_tools_allowed_entries',
                        message='Allowed tool list contains invalid entries.',
                        level='warning',
                    )
                )

    stores_section = definition_payload.get('stores')
    if isinstance(stores_section, Mapping):
        for store_name in ('artifact', 'checkpoint'):
            store_config = stores_section.get(store_name)
            if not isinstance(store_config, Mapping):
                continue
            if any(key in store_config for key in ('backend', 'config', 'root')):
                issues.append(
                    WorkflowConfigIssue(
                        path=f'stores.{store_name}',
                        code=f'reserved_{store_name}_store_config',
                        message=f'Workflow definition payload must not declare {store_name} store backend configuration.',
                        level='error',
                    )
                )

    allowed_tools = _extract_allowed_tool_names(definition_payload)

    supported = tuple(supported_graph_kinds or ())
    if supported and effective_graph_kind not in supported:
        issues.append(
            WorkflowConfigIssue(
                path='graph.kind',
                code='unknown_graph_kind',
                message=f'Unsupported graph kind: {effective_graph_kind}.',
                level='error',
            )
        )

    requirements = None if graph_requirements is None else graph_requirements.get(effective_graph_kind)
    if requirements is not None:
        if requirements.requires_llm and not llm_enabled:
            issues.append(
                WorkflowConfigIssue(
                    path='llm.enabled',
                    code='graph_requires_llm',
                    message=f'Graph {effective_graph_kind} requires llm.enabled=true.',
                    level='error',
                )
            )
        if requirements.required_tools:
            missing_tools = tuple(tool for tool in requirements.required_tools if tool not in allowed_tools)
            if missing_tools:
                issues.append(
                    WorkflowConfigIssue(
                        path='tools.allowed',
                        code='graph_missing_required_tools',
                        message=f'Graph {effective_graph_kind} expects allowed tools {list(missing_tools)}; continuing with policy deny behavior.',
                        level='warning',
                    )
                )

    return WorkflowConfigValidation(issues=tuple(issues))


def workflow_runtime_config_summary(definition_payload: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return a small summary of the raw workflow definition payload for debugging."""

    return summarize_mapping(definition_payload or {}) if isinstance(definition_payload, Mapping) else {'keys': [], 'types': {}, 'sizes': {}, 'preview': {}}
