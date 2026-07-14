"""Architecture guard for the llm_echo_summary reference diagnostic workflow boundaries."""

from __future__ import annotations

import ast
from pathlib import Path

BANNED_IMPORT_PREFIXES = (
    'django.db',
    'langgraph_automation.apps.automation.models',
    'langgraph_automation.config.settings',
    'litellm',
)
BANNED_FROM_IMPORTS = {
    ('langgraph_automation.integrations.llm.litellm_client', 'LiteLLMClient'),
    ('langgraph_automation.integrations.tools.safe_tools', 'EchoTool'),
}


def _module_imports(path: Path) -> list[tuple[str, str | None]]:
    tree = ast.parse(path.read_text())
    imports: list[tuple[str, str | None]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append((alias.name, None))
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            for alias in node.names:
                imports.append((node.module, alias.name))
    return imports


def test_reference_diagnostic_workflow_nodes_do_not_depend_on_concrete_persistence_or_provider_implementations() -> None:
    offenders: list[str] = []
    for path in Path('src/langgraph_automation/workflows/reference/llm_echo_summary').rglob('*.py'):
        for module, name in _module_imports(path):
            if module.startswith(BANNED_IMPORT_PREFIXES) or (module, name) in BANNED_FROM_IMPORTS:
                offenders.append(f'{path}:{module}:{name or "*"}')
                break
    assert offenders == []


def test_reference_diagnostic_workflow_package_exists_and_graphs_nodes_are_empty() -> None:
    workflow_root = Path('src/langgraph_automation/workflows/reference/llm_echo_summary')
    assert workflow_root.is_dir()
    assert (workflow_root / 'graph.py').exists()
    assert (workflow_root / 'nodes.py').exists()
    assert (workflow_root / 'state.py').exists()
    assert (workflow_root / 'definition.py').exists()

    legacy_nodes_root = Path('src/langgraph_automation/graphs/nodes')
    assert legacy_nodes_root.is_dir()
    assert not (legacy_nodes_root / 'minimal.py').exists()
    assert not (legacy_nodes_root / 'planner.py').exists()
    assert not (legacy_nodes_root / 'summarizer.py').exists()
