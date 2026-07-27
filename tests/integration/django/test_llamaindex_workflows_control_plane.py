from __future__ import annotations

import pytest
from workflows import Workflow as LlamaWorkflow, step
from workflows.events import Event, StartEvent, StopEvent

from cobalt_wren.api.plugins import (
    PLUGIN_API_VERSION,
    Plugin,
    PluginContributions,
    PluginMetadata,
)
from cobalt_wren.api.workflow import (
    WorkflowContribution,
    WorkflowDefinition,
    WorkflowMetadata,
    WorkflowRequirements,
)
from cobalt_wren.apps.automation.models import (
    ExecutionSpan,
    IntegrationProjectionRecord,
    Run,
    RunStatus,
    Workflow,
)
from cobalt_wren.apps.automation.services import runtime as runtime_module
from cobalt_wren.apps.automation.services.runs import start_run
from cobalt_wren.integrations.llamaindex_workflows import (
    integrate_llamaindex_workflow,
)


class Validated(Event):
    text: str


class DemoWorkflow(LlamaWorkflow):
    @step
    async def validate(self, ev: StartEvent) -> Validated:
        return Validated(text=str(ev.get("text", "")).strip())

    @step
    async def complete(self, ev: Validated) -> StopEvent:
        return StopEvent(result={"normalized": ev.text.upper()})


def _plugin() -> Plugin:
    executable = integrate_llamaindex_workflow(
        DemoWorkflow(timeout=5),
        workflow_kind="integration.llamaindex",
    )

    def build():
        return executable

    contribution = WorkflowContribution(
        kind="integration.llamaindex",
        definition=WorkflowDefinition(
            kind="integration.llamaindex",
            metadata=WorkflowMetadata(name="LlamaIndex integration", version="1"),
            requirements=WorkflowRequirements(),
            build=build,
        ),
    )
    return Plugin(
        metadata=PluginMetadata(
            name="integration.llamaindex.test",
            version="1",
            plugin_types=("workflow",),
            provides={"workflows": ("integration.llamaindex",)},
            metadata={"plugin_api_version": PLUGIN_API_VERSION},
        ),
        contributions=PluginContributions(workflows=(contribution,)),
    )


@pytest.mark.django_db
def test_llamaindex_workflow_uses_common_span_projection_and_ui(
    client, monkeypatch: pytest.MonkeyPatch
) -> None:
    services = runtime_module.build_run_execution_services(
        {"version": 1},
        plugins=(_plugin(),),
        discover_plugins=False,
    )
    monkeypatch.setattr(runtime_module, "get_run_execution_services", lambda: services)
    workflow = Workflow.objects.create(
        name="llamaindex-control-plane",
        definition_payload={"workflow": {"kind": "integration.llamaindex"}},
    )
    run = Run.objects.create(
        workflow=workflow,
        name="llamaindex-run",
        input_payload={"text": " hello "},
    )

    result = start_run(run=run, services=services).run

    assert result.status == RunStatus.SUCCEEDED
    assert result.output_payload["summary"]["preview"]["normalized"] == "HELLO"
    spans = list(ExecutionSpan.objects.filter(run=result).order_by("started_at"))
    assert [span.node_name for span in spans if span.span_type == "step"] == [
        "validate",
        "complete",
    ]
    assert all(span.status == "succeeded" for span in spans)
    records = IntegrationProjectionRecord.objects.filter(run=result)
    assert records.filter(schema_id="llamaindex.step.v1").count() == 4
    assert records.filter(schema_id="llamaindex.event.v1").exists()
    step_records = records.filter(schema_id="llamaindex.step.v1")
    assert set(step_records.values_list("projection_kind", flat=True)) == {"snapshot"}
    assert set(step_records.values_list("subject_kind", flat=True)) == {"execution_unit"}
    assert set(step_records.values_list("subject_external_id", flat=True)) == {"validate", "complete"}
    assert set(records.filter(schema_id="llamaindex.event.v1").values_list("projection_kind", flat=True)) == {"event"}

    run_page = client.get(f"/ui/runs/{result.pk}/")
    step_span = next(span for span in spans if span.span_type == "step")
    span_page = client.get(f"/ui/spans/{step_span.pk}/")
    run_html = run_page.content.decode()
    span_html = span_page.content.decode()

    assert run_page.status_code == 200
    assert span_page.status_code == 200
    assert 'data-component="integration.projection"' in run_html
    assert 'data-schema-id="llamaindex.step.v1"' in run_html
    assert 'data-component="integration.summary"' in run_html
    assert 'href="#integration-llamaindex-workflows"' in run_html
    assert "Execution units" in run_html
    assert "Projections" in run_html
    assert 'data-component="integration.current-state"' in run_html
    assert 'data-component="integration.timeline"' in run_html
    assert 'data-component="integration.technical-projections"' in run_html
    assert "validate" in run_html
    assert "complete" in run_html
    assert "LlamaIndex step: validate" in run_html
    assert 'data-schema-id="llamaindex.step.v1"' in span_html
