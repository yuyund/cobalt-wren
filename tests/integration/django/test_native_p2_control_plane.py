"""Django control-plane proof for Native P2 policies."""

from __future__ import annotations

import asyncio
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
from cobalt_wren.native import NativeWorkflowContext, RetryPolicy, workflow


@pytest.mark.django_db
def test_native_retry_attempts_persist_through_common_control_plane(client) -> None:
    attempts = 0

    async def unstable() -> str:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ConnectionError("private transient failure")
        return "ready"

    @workflow(name="Native retry control plane")
    async def retry_workflow(
        ctx: NativeWorkflowContext,
        request: Mapping[str, object],
    ) -> Mapping[str, object]:
        del request
        value = await ctx.step(
            "remote-call",
            unstable,
            retry=RetryPolicy(max_attempts=3, retry_on=(ConnectionError,)),
        )
        return {"value": value}

    plugin = retry_workflow.plugin(
        plugin_name="native-retry-control-plane",
        workflow_kind="integration.native.retry",
    )
    services = runtime_module.build_run_execution_services(
        {"version": 1}, plugins=(plugin,), discover_plugins=False
    )
    workflow_model = Workflow.objects.create(
        name="native-retry",
        definition_payload={"workflow": {"kind": "integration.native.retry"}},
    )
    run = Run.objects.create(workflow=workflow_model, name="native-retry-run")

    result = start_run(run=run, services=services).run

    assert result.status == RunStatus.SUCCEEDED
    assert attempts == 3
    spans = list(
        ExecutionSpan.objects.filter(run=result, span_type="step").order_by("pk")
    )
    assert [span.status for span in spans] == ["failed", "failed", "succeeded"]
    assert [span.metadata["attempt"] for span in spans] == [1, 2, 3]
    assert "private transient failure" not in str([span.error_message for span in spans])

    records = list(
        IntegrationProjectionRecord.objects.filter(
            run=result,
            integration_id="native",
            schema_id="native.step.v1",
        ).order_by("sequence", "pk")
    )
    assert [record.payload["status"] for record in records] == [
        "running",
        "retrying",
        "running",
        "retrying",
        "running",
        "succeeded",
    ]
    assert {record.subject_external_id for record in records} == {"remote-call"}

    response = client.get(f"/ui/runs/{result.pk}/")
    html = response.content.decode()
    assert response.status_code == 200
    assert "retrying" in html
    assert "remote-call" in html


@pytest.mark.django_db
def test_native_step_timeout_becomes_timed_out_run() -> None:
    async def slow() -> str:
        await asyncio.sleep(0.1)
        return "late"

    @workflow(name="Native timeout control plane")
    async def timeout_workflow(
        ctx: NativeWorkflowContext,
        request: Mapping[str, object],
    ) -> Mapping[str, object]:
        del request
        await ctx.step("slow", slow, timeout_seconds=0.01)
        return {}

    plugin = timeout_workflow.plugin(
        plugin_name="native-timeout-control-plane",
        workflow_kind="integration.native.timeout",
    )
    services = runtime_module.build_run_execution_services(
        {"version": 1}, plugins=(plugin,), discover_plugins=False
    )
    workflow_model = Workflow.objects.create(
        name="native-timeout",
        definition_payload={"workflow": {"kind": "integration.native.timeout"}},
    )
    run = Run.objects.create(workflow=workflow_model, name="native-timeout-run")

    action = start_run(run=run, services=services)

    assert action.run.status == RunStatus.TIMED_OUT
    assert action.execution_result is not None
    assert action.execution_result.details["error_code"] == "WORKFLOW_TIMED_OUT"
    span = ExecutionSpan.objects.get(run=action.run, span_type="step")
    assert span.status == "failed"
    assert span.error_message == "Native step execution failed."
    terminal = IntegrationProjectionRecord.objects.filter(
        run=action.run,
        integration_id="native",
        schema_id="native.step.v1",
    ).order_by("-sequence", "-pk").first()
    assert terminal is not None
    assert terminal.payload["status"] == "failed"
