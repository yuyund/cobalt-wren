"""Architecture guard for the minimal LLM + EchoTool workflow boundaries."""

from __future__ import annotations

from pathlib import Path


BANNED_NODE_IMPORTS = (
    'django.db',
    'apps.automation.models',
    'config.settings',
    'LiteLLMClient',
    'litellm',
    'from langgraph_automation.integrations.tools.safe_tools import EchoTool',
    'integrations.tools.safe_tools import EchoTool',
    'EchoTool(',
    'Run.objects',
    'Workflow.objects',
    'RunEvent.objects',
    'ExecutionSpan.objects',
)


def test_minimal_workflow_nodes_do_not_depend_on_concrete_persistence_or_provider_implementations() -> None:
    offenders: list[str] = []
    for path in Path('src/langgraph_automation/graphs/nodes').rglob('*.py'):
        text = path.read_text()
        if any(term in text for term in BANNED_NODE_IMPORTS):
            offenders.append(str(path))
    assert offenders == []
