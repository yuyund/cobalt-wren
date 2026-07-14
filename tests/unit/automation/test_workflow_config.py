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
from langgraph_automation.graphs.registry import default_graph_kind
from langgraph_automation.workflows.catalog import build_builtin_graph_registry


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


def test_validate_workflow_runtime_config_warns_when_graph_kind_is_missing_or_empty() -> None:
    validation = validate_workflow_runtime_config(
        {
            'llm': {
                'enabled': True,
                'model': 'gpt-4o-mini',
            },
            'tools': {
                'allowed': ['echo'],
            },
        },
        supported_graph_kinds=build_builtin_graph_registry().supported_graph_kinds(),
        graph_requirements=build_builtin_graph_registry().graph_requirements(),
    )

    assert validation.has_errors is False
    assert any(issue.path == 'graph.kind' and issue.code == 'missing_graph_kind' for issue in validation.issues)
    assert not any(issue.path == 'tools.allowed' and issue.code == 'graph_missing_required_tools' for issue in validation.issues)

    validation_empty = validate_workflow_runtime_config(
        {
            'graph': {
                'kind': '   ',
            },
            'llm': {
                'enabled': True,
                'model': 'gpt-4o-mini',
            },
            'tools': {
                'allowed': ['echo'],
            },
        },
        supported_graph_kinds=build_builtin_graph_registry().supported_graph_kinds(),
        graph_requirements=build_builtin_graph_registry().graph_requirements(),
    )

    assert validation_empty.has_errors is False
    assert any(issue.path == 'graph.kind' and issue.code == 'empty_graph_kind' for issue in validation_empty.issues)


def test_validate_workflow_runtime_config_treats_non_string_graph_kind_as_warning() -> None:
    validation = validate_workflow_runtime_config(
        {
            'graph': {
                'kind': 123,
            },
            'llm': {
                'enabled': True,
                'model': 'gpt-4o-mini',
            },
            'tools': {
                'allowed': ['echo'],
            },
        },
        supported_graph_kinds=build_builtin_graph_registry().supported_graph_kinds(),
        graph_requirements=build_builtin_graph_registry().graph_requirements(),
    )

    assert validation.has_errors is False
    assert any(issue.path == 'graph.kind' and issue.code == 'invalid_graph_kind_type' for issue in validation.issues)


def test_validate_workflow_runtime_config_rejects_unknown_graph_kind() -> None:
    validation = validate_workflow_runtime_config(
        {
            'graph': {
                'kind': 'unknown-kind',
            },
            'llm': {
                'enabled': True,
                'model': 'gpt-4o-mini',
            },
            'tools': {
                'allowed': ['echo'],
            },
        },
        supported_graph_kinds=build_builtin_graph_registry().supported_graph_kinds(),
        graph_requirements=build_builtin_graph_registry().graph_requirements(),
    )

    assert validation.has_errors is True
    assert any(issue.path == 'graph.kind' and issue.code == 'unknown_graph_kind' for issue in validation.issues)


def test_validate_workflow_runtime_config_requires_llm_for_minimal_graph() -> None:
    validation = validate_workflow_runtime_config(
        {
            'graph': {
                'kind': default_graph_kind(),
            },
            'llm': {
                'enabled': False,
            },
            'tools': {
                'allowed': ['echo'],
            },
        },
        supported_graph_kinds=build_builtin_graph_registry().supported_graph_kinds(),
        graph_requirements=build_builtin_graph_registry().graph_requirements(),
    )

    assert validation.has_errors is True
    assert any(issue.path == 'llm.enabled' and issue.code == 'graph_requires_llm' for issue in validation.issues)


def test_validate_workflow_runtime_config_requires_llm_model_when_enabled() -> None:
    validation = validate_workflow_runtime_config(
        {
            'graph': {
                'kind': default_graph_kind(),
            },
            'llm': {
                'enabled': True,
            },
            'tools': {
                'allowed': ['echo'],
            },
        },
        supported_graph_kinds=build_builtin_graph_registry().supported_graph_kinds(),
        graph_requirements=build_builtin_graph_registry().graph_requirements(),
    )

    assert validation.has_errors is True
    assert any(issue.path == 'llm.model' and issue.code == 'missing_llm_model' for issue in validation.issues)


def test_validate_workflow_runtime_config_warns_when_echo_is_missing() -> None:
    validation = validate_workflow_runtime_config(
        {
            'graph': {
                'kind': default_graph_kind(),
            },
            'llm': {
                'enabled': True,
                'model': 'gpt-4o-mini',
            },
            'tools': {
                'allowed': [],
            },
        },
        supported_graph_kinds=build_builtin_graph_registry().supported_graph_kinds(),
        graph_requirements=build_builtin_graph_registry().graph_requirements(),
    )

    assert validation.has_errors is False
    assert any(issue.path == 'tools.allowed' and issue.code == 'graph_missing_required_tools' for issue in validation.issues)


def test_validate_workflow_runtime_config_warns_when_tools_allowed_is_not_a_list() -> None:
    validation = validate_workflow_runtime_config(
        {
            'graph': {
                'kind': default_graph_kind(),
            },
            'llm': {
                'enabled': True,
                'model': 'gpt-4o-mini',
            },
            'tools': {
                'allowed': 'echo',
            },
        },
        supported_graph_kinds=build_builtin_graph_registry().supported_graph_kinds(),
        graph_requirements=build_builtin_graph_registry().graph_requirements(),
    )

    assert validation.has_errors is False
    assert any(issue.path == 'tools.allowed' and issue.code == 'invalid_tools_allowed_type' for issue in validation.issues)
    assert any(issue.path == 'tools.allowed' and issue.code == 'graph_missing_required_tools' for issue in validation.issues)
