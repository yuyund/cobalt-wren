'''PageSpec tests for run detail rendering.'''

from __future__ import annotations

import pytest

from cobalt_wren.apps.automation.models.run import Run, RunStatus
from cobalt_wren.apps.automation.models.workflow import Workflow
from cobalt_wren.apps.automation.ui.builders import build_detail_page_spec, build_fragment_spec
from cobalt_wren.apps.automation.ui.registry import get_model_ui_config


@pytest.mark.django_db
def test_runs_detail_pagespec_uses_registered_fields() -> None:
    workflow = Workflow.objects.create(name='wf-pagespec')
    run = Run.objects.create(
        workflow=workflow,
        name='run-pagespec',
        status=RunStatus.PENDING,
        input_payload={'api_key': 'secret'},
    )

    spec = build_detail_page_spec('runs', run.pk)
    config = get_model_ui_config('runs')

    assert spec.model_key == 'runs'
    assert spec.object_id == run.pk
    assert spec.title == 'Run'
    assert [field.name for field in spec.fields] == config.detail_fields
    assert len(spec.related_sections) == 4
    assert all(section.table is not None for section in spec.related_sections)
    assert {section.model_key for section in spec.related_sections} == {'spans', 'events', 'artifacts', 'checkpoints'}


@pytest.mark.django_db
def test_runs_fragment_pagespec_is_registry_driven() -> None:
    workflow = Workflow.objects.create(name='wf-fragment-spec')
    run = Run.objects.create(workflow=workflow, name='run-fragment-spec')

    fragment = build_fragment_spec('runs', run.pk, 'spans')

    assert fragment.model_key == 'runs'
    assert fragment.fragment_name == 'spans'
    assert fragment.title == 'Execution Spans'
    assert fragment.table.empty_message == 'No spans yet'


@pytest.mark.django_db
def test_hidden_fields_are_not_auto_added() -> None:
    workflow = Workflow.objects.create(name='wf-hidden')
    run = Run.objects.create(workflow=workflow, name='run-hidden')

    spec = build_detail_page_spec('runs', run)
    field_names = {field.name for field in spec.fields}

    assert 'workflow' in field_names
    assert 'input_payload' not in field_names
    assert 'input_payload_summary' in field_names
