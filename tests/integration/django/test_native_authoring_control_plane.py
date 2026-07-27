"""Django control-plane vertical proof for Native Authoring."""

from __future__ import annotations

from collections.abc import Mapping

import pytest

from cobalt_wren.apps.automation.models import (
    ExecutionSpan,
    IntegrationProjectionRecord,
    Run,
    RunStatus,
    Workflow,
)
from cobalt_wren.apps.automation.services import runtime as runtime_module
from cobalt_wren.apps.automation.services.runs import start_run
from cobalt_wren.native import NativeWorkflowContext, workflow


@workflow(name="Native document review", version="1.0.0")
async def native_document_review(
    ctx: NativeWorkflowContext,
    request: Mapping[str, object],
) -> Mapping[str, object]:
    normalized = await ctx.step("normalize", _normalize, str(request["text"]))
    if bool(request.get("uppercase")):
        rendered = await ctx.step("render-uppercase", _uppercase, normalized)
    else:
        rendered = await ctx.step("render-lowercase", _lowercase, normalized)
    return {"rendered": rendered}


def _normalize(value: str) -> str:
    return value.strip()


async def _uppercase(value: str) -> str:
    return value.upper()


async def _lowercase(value: str) -> str:
    return value.lower()


@pytest.mark.django_db
def test_native_workflow_uses_public_contribution_common_persistence_and_ui(client) -> None:
    plugin = native_document_review.plugin(
        plugin_name="native-document-review-plugin",
        workflow_kind="integration.native.document-review",
    )
    services = runtime_module.build_run_execution_services(
        {"version": 1},
        plugins=(plugin,),
        discover_plugins=False,
    )
    workflow_model = Workflow.objects.create(
        name="native-document-review",
        definition_payload={
            "workflow": {"kind": "integration.native.document-review"}
        },
    )
    run = Run.objects.create(
        workflow=workflow_model,
        name="native-document-review-run",
        input_payload={"text": " Hello Native ", "uppercase": True},
    )

    result = start_run(run=run, services=services).run

    assert result.status == RunStatus.SUCCEEDED
    assert result.output_payload["summary"]["preview"]["rendered"] == "HELLO NATIVE"
    spans = list(ExecutionSpan.objects.filter(run=result).order_by("started_at", "pk"))
    step_spans = [span for span in spans if span.span_type == "step"]
    assert [span.node_name for span in step_spans] == [
        "normalize",
        "render-uppercase",
    ]
    assert all(span.status == "succeeded" for span in step_spans)

    records = IntegrationProjectionRecord.objects.filter(
        run=result,
        integration_id="native",
        schema_id="native.step.v1",
    )
    assert records.count() == 4
    assert set(records.values_list("projection_kind", flat=True)) == {"snapshot"}
    assert set(records.values_list("subject_kind", flat=True)) == {
        "execution_unit"
    }
    assert set(records.values_list("subject_external_id", flat=True)) == {
        "normalize",
        "render-uppercase",
    }

    response = client.get(f"/ui/runs/{result.pk}/")
    html = response.content.decode()
    assert response.status_code == 200
    assert 'data-component="integration.summary"' in html
    assert 'href="#integration-native"' in html
    assert 'data-component="integration.current-state"' in html
    assert 'data-component="integration.timeline"' in html
    assert 'data-component="integration.technical-projections"' in html
    assert 'data-schema-id="native.step.v1"' in html
    assert "Native step: normalize" in html
    assert "Native step: render-uppercase" in html
