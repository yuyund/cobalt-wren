"""Workflow runtime config parsing and validation helpers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from langgraph_automation.core.summary import summarize_mapping


@dataclass(frozen=True)
class LLMWorkflowConfig:
    """Normalized workflow-level LLM configuration."""

    enabled: bool = False
    model: str = ""
    temperature: float | None = None
    max_tokens: int | None = None


@dataclass(frozen=True)
class ToolWorkflowConfig:
    """Normalized workflow-level tool policy configuration."""

    allowed_tools: tuple[str, ...] = ()


@dataclass(frozen=True)
class WorkflowRuntimeConfig:
    """Normalized runtime configuration extracted from Workflow.definition_payload."""

    llm: LLMWorkflowConfig = field(default_factory=LLMWorkflowConfig)
    tools: ToolWorkflowConfig = field(default_factory=ToolWorkflowConfig)


@dataclass(frozen=True)
class WorkflowConfigIssue:
    path: str
    code: str
    message: str
    level: str = "error"


@dataclass(frozen=True)
class WorkflowConfigValidation:
    issues: tuple[WorkflowConfigIssue, ...] = ()

    @property
    def has_errors(self) -> bool:
        return any(issue.level == 'error' for issue in self.issues)


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


def _is_numeric_value(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


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


def parse_workflow_runtime_config(definition_payload: Mapping[str, Any] | None) -> WorkflowRuntimeConfig:
    """Parse a workflow definition payload into normalized runtime config."""

    return WorkflowRuntimeConfig(
        llm=_parse_llm_config(definition_payload),
        tools=ToolWorkflowConfig(allowed_tools=_extract_allowed_tool_names(definition_payload)),
    )


def validate_workflow_runtime_config(definition_payload: Mapping[str, Any] | None) -> WorkflowConfigValidation:
    """Validate workflow runtime configuration and return normalized issues."""

    issues: list[WorkflowConfigIssue] = []
    if not isinstance(definition_payload, Mapping):
        issues.append(WorkflowConfigIssue(path='definition_payload', code='invalid_mapping', message='Workflow definition payload must be a mapping.', level='warning'))
        return WorkflowConfigValidation(issues=tuple(issues))

    llm = definition_payload.get('llm')
    if llm is None:
        issues.append(WorkflowConfigIssue(path='llm', code='missing_llm', message='LLM configuration is missing.', level='warning'))
    elif not isinstance(llm, Mapping):
        issues.append(WorkflowConfigIssue(path='llm', code='invalid_llm_type', message='LLM configuration must be a mapping.', level='warning'))
    else:
        enabled = llm.get('enabled', False)
        if not isinstance(enabled, bool):
            issues.append(WorkflowConfigIssue(path='llm.enabled', code='invalid_llm_enabled_type', message='LLM enabled flag must be a boolean.', level='error'))
        if enabled is True:
            model = llm.get('model')
            if not isinstance(model, str) or not model.strip():
                issues.append(WorkflowConfigIssue(path='llm.model', code='missing_llm_model', message='LLM model is required when LLM is enabled.', level='error'))
        temperature = llm.get('temperature')
        if temperature is not None and not _is_numeric_value(temperature):
            issues.append(WorkflowConfigIssue(path='llm.temperature', code='invalid_llm_temperature', message='LLM temperature must be numeric.', level='warning'))
        max_tokens = llm.get('max_tokens')
        if max_tokens is not None and not _is_positive_int(max_tokens):
            issues.append(WorkflowConfigIssue(path='llm.max_tokens', code='invalid_llm_max_tokens', message='LLM max_tokens must be a positive integer.', level='warning'))

    tools = definition_payload.get('tools')
    if tools is None:
        issues.append(WorkflowConfigIssue(path='tools', code='missing_tools', message='Tool configuration is missing.', level='warning'))
    elif not isinstance(tools, Mapping):
        issues.append(WorkflowConfigIssue(path='tools', code='invalid_tools_type', message='Tool configuration must be a mapping.', level='warning'))
    else:
        allowed = tools.get('allowed')
        if allowed is None:
            issues.append(WorkflowConfigIssue(path='tools.allowed', code='missing_tools_allowed', message='Allowed tool list is missing.', level='warning'))
        elif not isinstance(allowed, list):
            issues.append(WorkflowConfigIssue(path='tools.allowed', code='invalid_tools_allowed_type', message='Allowed tool list must be a list.', level='warning'))
        else:
            invalid_items = [entry for entry in allowed if not isinstance(entry, str) or not entry.strip()]
            if invalid_items:
                issues.append(WorkflowConfigIssue(path='tools.allowed', code='invalid_tools_allowed_entries', message='Allowed tool list contains invalid entries.', level='warning'))

    return WorkflowConfigValidation(issues=tuple(issues))


def workflow_runtime_config_summary(definition_payload: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return a small summary of the raw workflow definition payload for debugging."""

    return summarize_mapping(definition_payload or {}) if isinstance(definition_payload, Mapping) else {'keys': [], 'types': {}, 'sizes': {}, 'preview': {}}
