"""Architecture guard for safety exposure boundaries."""

from __future__ import annotations

from pathlib import Path

from django.contrib import admin
from django.test import RequestFactory

from langgraph_automation.apps.automation.admin import RunAdmin, WorkflowAdmin
from langgraph_automation.apps.automation.models.run import Run
from langgraph_automation.apps.automation.models.workflow import Workflow
from langgraph_automation.apps.automation.ui.registry import get_model_ui_config


def test_templates_do_not_use_raw_debug_dumps() -> None:
    root = Path('src/langgraph_automation/apps/web/templates')
    offenders: list[str] = []
    forbidden_tokens = ('__dict__', '_meta', 'pprint', 'debug', 'json.dumps(')

    for path in root.rglob('*.html'):
        text = path.read_text()
        if any(token in text for token in forbidden_tokens):
            offenders.append(str(path))

    assert offenders == []


def test_admin_forms_expose_safe_summary_fields_for_raw_payload_models() -> None:
    request = RequestFactory().get('/admin/')
    run_admin = admin.site._registry[Run]
    workflow_admin = admin.site._registry[Workflow]

    assert isinstance(run_admin, RunAdmin)
    assert isinstance(workflow_admin, WorkflowAdmin)

    assert 'input_payload' not in run_admin.get_fields(request)
    assert 'definition_payload' not in workflow_admin.get_fields(request)
    assert 'input_payload_summary' in run_admin.get_fields(request)
    assert 'definition_payload_summary' in workflow_admin.get_fields(request)


def test_ui_registry_visible_fields_use_safe_summary_names() -> None:
    forbidden = {'definition_payload', 'input_payload', 'output_payload', 'payload', 'metadata'}
    for model_key in ('workflows', 'runs', 'spans', 'events', 'artifacts', 'checkpoints'):
        config = get_model_ui_config(model_key)
        assert config is not None
        visible_fields = set(config.list_fields) | set(config.detail_fields)
        assert not (visible_fields & forbidden)

    runs = get_model_ui_config('runs')
    spans = get_model_ui_config('spans')
    events = get_model_ui_config('events')
    artifacts = get_model_ui_config('artifacts')

    assert runs is not None
    assert spans is not None
    assert events is not None
    assert artifacts is not None

    assert 'input_payload_summary' in runs.detail_fields
    assert 'output_payload_summary' in runs.detail_fields
    assert 'metadata_summary' in spans.detail_fields
    assert 'metrics_summary' in spans.detail_fields
    assert 'payload_summary' in events.detail_fields
    assert 'metadata_summary' in artifacts.detail_fields
