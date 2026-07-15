"""Architecture guard for built-in workflow wiring boundaries."""

from __future__ import annotations

import ast
from pathlib import Path


def _imported_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text())
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.append(node.module)
    return modules


def test_workflow_catalog_uses_public_facades_and_internal_bridge_only() -> None:
    modules = _imported_modules(Path('src/langgraph_automation/workflows/catalog.py'))

    assert 'langgraph_automation.api.plugins' in modules
    assert 'langgraph_automation.api.workflow' in modules
    assert 'langgraph_automation.plugins.registry' in modules
    assert 'langgraph_automation.workflows.adapter' in modules
    assert 'langgraph_automation.workflows.reference.llm_echo_summary.definition' in modules
    assert 'langgraph_automation.graphs.registry' in modules

    offenders = [
        module
        for module in modules
        if module.startswith(
            (
                'langgraph_automation.runtime',
                'langgraph_automation.config.validator',
                'langgraph_automation.apps.automation',
                'django',
            )
        )
    ]
    assert offenders == []


def test_workflow_adapter_stays_inside_workflow_and_error_facades() -> None:
    modules = _imported_modules(Path('src/langgraph_automation/workflows/adapter.py'))

    assert 'langgraph_automation.api.errors' in modules
    assert 'langgraph_automation.api.workflow' in modules
    offenders = [module for module in modules if module.startswith('langgraph_automation.runtime')]
    assert offenders == []


def test_workflow_requirements_checker_depends_on_runtime_dependencies_only() -> None:
    modules = _imported_modules(Path('src/langgraph_automation/workflows/requirements.py'))

    assert 'langgraph_automation.api.errors' in modules
    assert 'langgraph_automation.api.workflow' in modules
    assert 'langgraph_automation.runtime.dependencies' in modules
    offenders = [module for module in modules if module.startswith('langgraph_automation.apps.automation')]
    assert offenders == []


def test_reference_workflow_definition_stays_within_internal_graph_boundary() -> None:
    modules = _imported_modules(Path('src/langgraph_automation/workflows/reference/llm_echo_summary/definition.py'))

    assert 'langgraph_automation.api.workflow' in modules
    assert 'langgraph_automation.graphs.constants' in modules
    assert 'langgraph_automation.graphs.types' in modules
    assert 'graph' in modules or 'langgraph_automation.workflows.reference.llm_echo_summary.graph' in modules
    offenders = [module for module in modules if module.startswith('langgraph_automation.runtime')]
    assert offenders == []
