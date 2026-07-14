"""Workflow runtime config parsing tests."""

from __future__ import annotations

from langgraph_automation.apps.automation.services.workflow_config import (
    GraphWorkflowConfig,
    LLMWorkflowConfig,
    MINIMAL_GRAPH_KIND,
    ToolWorkflowConfig,
    WorkflowRuntimeConfig,
    extract_allowed_tool_names,
    parse_workflow_runtime_config,
    validate_workflow_runtime_config,
)


def test_parse_workflow_runtime_config_defaults_to_safe_values() -> None:
    config = parse_workflow_runtime_config(None)

    assert config == WorkflowRuntimeConfig(graph=GraphWorkflowConfig(), llm=LLMWorkflowConfig(), tools=ToolWorkflowConfig())
    assert config.graph.kind == MINIMAL_GRAPH_KIND
    assert config.llm.enabled is False
    assert config.tools.allowed_tools == ()


def test_parse_workflow_runtime_config_normalizes_graph_llm_and_tools() -> None:
    config = parse_workflow_runtime_config(
        {
            'graph': {
                'kind': 'llm_echo_summary',
            },
            'llm': {
                'enabled': True,
                'model': 'gpt-4o-mini',
                'temperature': 0.2,
                'max_tokens': 1024,
            },
            'tools': {
                'allowed': ['echo', ' ', 'echo', 123],
            },
        }
    )

    assert config.graph == GraphWorkflowConfig(kind='llm_echo_summary')
    assert config.llm.enabled is True
    assert config.llm.model == 'gpt-4o-mini'
    assert config.llm.temperature == 0.2
    assert config.llm.max_tokens == 1024
    assert config.tools.allowed_tools == ('echo',)


def test_parse_workflow_runtime_config_rejects_bool_numeric_values() -> None:
    config = parse_workflow_runtime_config(
        {
            'llm': {
                'enabled': True,
                'model': 'gpt-4o-mini',
                'temperature': True,
                'max_tokens': True,
            }
        }
    )

    assert config.llm.enabled is True
    assert config.llm.model == 'gpt-4o-mini'
    assert config.llm.temperature is None
    assert config.llm.max_tokens is None


def test_extract_allowed_tool_names_defaults_to_deny_all() -> None:
    assert extract_allowed_tool_names(None) == ()
    assert extract_allowed_tool_names({}) == ()
    assert extract_allowed_tool_names({'tools': {}}) == ()
    assert extract_allowed_tool_names({'tools': {'allowed': []}}) == ()
    assert extract_allowed_tool_names({'tools': {'allowed': 'echo'}}) == ()


def test_validate_workflow_runtime_config_reports_expected_issues() -> None:
    validation = validate_workflow_runtime_config(
        {
            'graph': {
                'kind': 'unknown-kind',
            },
            'llm': {
                'enabled': 'yes',
                'temperature': 'warm',
                'max_tokens': True,
            },
            'tools': {
                'allowed': ['echo', '', 123],
            },
        }
    )

    assert validation.has_errors is True
    assert any(issue.path == 'graph.kind' for issue in validation.issues)
    assert any(issue.path == 'llm.enabled' for issue in validation.issues)
    assert any(issue.path == 'llm.temperature' for issue in validation.issues)
    assert any(issue.path == 'llm.max_tokens' for issue in validation.issues)
    assert any(issue.path == 'tools.allowed' for issue in validation.issues)
