from __future__ import annotations

from typing import TypedDict

import pytest
from django.test import override_settings
from django.urls import reverse
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

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
    IntegrationProjectionRecord,
    OperationAuditLog,
    Run,
    RunStatus,
    Workflow,
)
from cobalt_wren.apps.automation.services import runtime as runtime_module
from cobalt_wren.apps.automation.services.runs import start_run
from cobalt_wren.integrations.langgraph import integrate_langgraph


class ApprovalState(TypedDict, total=False):
    decision: object


def _approval_plugin() -> Plugin:
    def approval(state: ApprovalState) -> ApprovalState:
        del state
        return {"decision": interrupt({"kind": "approval"})}

    graph = StateGraph(ApprovalState)
    graph.add_node("approval", approval)
    graph.add_edge(START, "approval")
    graph.add_edge("approval", END)
    executable = integrate_langgraph(
        graph.compile(checkpointer=InMemorySaver()),
        workflow_kind="integration.approval",
    )

    def build():
        return executable

    contribution = WorkflowContribution(
        kind="integration.approval",
        definition=WorkflowDefinition(
            kind="integration.approval",
            metadata=WorkflowMetadata(name="Integration approval", version="1"),
            requirements=WorkflowRequirements(),
            build=build,
        ),
    )
    return Plugin(
        metadata=PluginMetadata(
            name="integration.action.test",
            version="1",
            plugin_types=("workflow",),
            provides={"workflows": ("integration.approval",)},
            metadata={"plugin_api_version": PLUGIN_API_VERSION},
        ),
        contributions=PluginContributions(workflows=(contribution,)),
    )


@pytest.mark.django_db
def test_langgraph_interrupt_projects_common_action_and_resumes_from_ui(
    client, monkeypatch: pytest.MonkeyPatch
) -> None:
    services = runtime_module.build_run_execution_services(
        {"version": 1},
        plugins=(_approval_plugin(),),
        discover_plugins=False,
    )
    monkeypatch.setattr(runtime_module, "get_run_execution_services", lambda: services)
    workflow = Workflow.objects.create(
        name="integration-action-workflow",
        definition_payload={"workflow": {"kind": "integration.approval"}},
    )
    run = Run.objects.create(
        workflow=workflow,
        name="integration-action-run",
        input_payload={},
    )

    started = start_run(run=run, services=services).run

    assert started.status == RunStatus.WAITING
    action_record = IntegrationProjectionRecord.objects.get(
        run=started,
        schema_id="integration.actions.v1",
    )
    action_name = f"integration-{action_record.pk}-resume"

    detail = client.get(
        reverse(
            "dynamic-detail",
            kwargs={"model_key": "runs", "object_id": started.pk},
        )
    )
    html = detail.content.decode()
    assert detail.status_code == 200
    assert "Resume" in html
    assert 'name="value"' in html
    assert action_name in html

    response = client.post(
        reverse(
            "dynamic-action",
            kwargs={
                "model_key": "runs",
                "object_id": started.pk,
                "action_name": action_name,
            },
        ),
        {"value": "approve"},
    )
    started.refresh_from_db()

    assert response.status_code == 200
    assert started.status == RunStatus.SUCCEEDED
    assert started.output_payload["summary"]["preview"]["decision"]["preview"] == {
        "value": "approve"
    }
    audit = OperationAuditLog.objects.filter(
        run=started,
        action=action_name,
        outcome="succeeded",
    ).latest("created_at")
    assert "approve" in str(audit.payload_summary)


@pytest.mark.django_db
def test_integration_action_is_revalidated_against_current_run_state(
    client, monkeypatch: pytest.MonkeyPatch
) -> None:
    services = runtime_module.build_run_execution_services(
        {"version": 1},
        plugins=(_approval_plugin(),),
        discover_plugins=False,
    )
    monkeypatch.setattr(runtime_module, "get_run_execution_services", lambda: services)
    workflow = Workflow.objects.create(
        name="integration-action-revalidate-workflow",
        definition_payload={"workflow": {"kind": "integration.approval"}},
    )
    run = Run.objects.create(workflow=workflow, name="integration-action-revalidate-run")
    waiting = start_run(run=run, services=services).run
    record = IntegrationProjectionRecord.objects.get(
        run=waiting,
        schema_id="integration.actions.v1",
    )
    action_name = f"integration-{record.pk}-resume"
    waiting.status = RunStatus.CANCELLED
    waiting.save(update_fields=["status", "updated_at"])

    response = client.post(
        reverse(
            "dynamic-action",
            kwargs={
                "model_key": "runs",
                "object_id": waiting.pk,
                "action_name": action_name,
            },
        ),
        {"value": "approve"},
    )

    assert response.status_code == 403


@pytest.mark.django_db
@override_settings(COBALT_WREN_EXECUTION_MODE="worker")
def test_integration_action_routes_through_execution_job_in_worker_mode(
    client, monkeypatch: pytest.MonkeyPatch
) -> None:
    from cobalt_wren.apps.automation.models import (
        ExecutionJob,
        ExecutionJobOperation,
        ExecutionJobStatus,
    )
    from cobalt_wren.apps.automation.services.jobs import execute_job

    services = runtime_module.build_run_execution_services(
        {"version": 1},
        plugins=(_approval_plugin(),),
        discover_plugins=False,
    )
    monkeypatch.setattr(runtime_module, "get_run_execution_services", lambda: services)
    workflow = Workflow.objects.create(
        name="integration-action-worker-workflow",
        definition_payload={"workflow": {"kind": "integration.approval"}},
    )
    run = Run.objects.create(workflow=workflow, name="integration-action-worker-run")
    waiting = start_run(run=run, services=services).run
    record = IntegrationProjectionRecord.objects.get(
        run=waiting,
        schema_id="integration.actions.v1",
    )
    action_name = f"integration-{record.pk}-resume"

    response = client.post(
        reverse(
            "dynamic-action",
            kwargs={
                "model_key": "runs",
                "object_id": waiting.pk,
                "action_name": action_name,
            },
        ),
        {"value": "approve"},
    )

    assert response.status_code == 200
    job = ExecutionJob.objects.get(run=waiting)
    assert job.operation == ExecutionJobOperation.RESUME
    assert job.status == ExecutionJobStatus.QUEUED
    assert job.payload == {"value": "approve"}

    execute_job(job)
    job.refresh_from_db()
    waiting.refresh_from_db()
    assert job.status == ExecutionJobStatus.SUCCEEDED
    assert waiting.status == RunStatus.SUCCEEDED
