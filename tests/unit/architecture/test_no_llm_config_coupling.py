"""Architecture guard for LLM config parsing and adapter boundaries."""

from __future__ import annotations

import ast
from pathlib import Path

BANNED_WORKFLOW_CONFIG_IMPORTS = (
    'django.db',
    'langgraph_automation.apps.automation.models',
    'langgraph_automation.graphs.builders',
    'langgraph_automation.graphs.nodes',
    'langgraph_automation.integrations.llm.litellm_client',
    'langgraph_automation.integrations.tools.safe_tools',
    'langgraph_automation.config.settings',
)


def _imported_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text())
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.append(node.module)
    return modules


def test_workflow_config_parser_is_pure_and_does_not_depend_on_django_or_graphs() -> None:
    path = Path('src/langgraph_automation/apps/automation/services/workflow_config.py')
    modules = _imported_modules(path)

    offenders = [module for module in modules if module.startswith(BANNED_WORKFLOW_CONFIG_IMPORTS)]
    assert offenders == []


def test_litellm_client_does_not_import_django_or_graphs() -> None:
    path = Path('src/langgraph_automation/integrations/llm/litellm_client.py')
    modules = _imported_modules(path)

    offenders = [module for module in modules if module.startswith(('django.db', 'langgraph_automation.apps.automation', 'langgraph_automation.graphs'))]
    assert offenders == []
