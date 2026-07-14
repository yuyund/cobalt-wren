"""Architecture guard for LLM config parsing and adapter boundaries."""

from __future__ import annotations

from pathlib import Path


def test_workflow_config_parser_is_pure_and_does_not_depend_on_django_or_graphs() -> None:
    text = Path('src/langgraph_automation/apps/automation/services/workflow_config.py').read_text()
    assert 'django.db' not in text
    assert 'apps.automation.models' not in text
    assert 'graphs.' not in text
    assert 'EventSink' not in text


def test_litellm_client_does_not_import_django_or_graphs() -> None:
    text = Path('src/langgraph_automation/integrations/llm/litellm_client.py').read_text()
    assert 'django.db' not in text
    assert 'apps.automation' not in text
    assert 'graphs.' not in text
