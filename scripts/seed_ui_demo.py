#!/usr/bin/env python3
"""Create reproducible UI demo data through real control-plane execution paths."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
for package in ("human_approval_workflow", "saga_workflow", "plain_python_workflow"):
    sys.path.insert(0, str(ROOT / "packages" / package / "src"))
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cobalt_wren.config.settings")

import django  # noqa: E402

django.setup()

from django.core.management import call_command  # noqa: E402
from django.db import transaction  # noqa: E402

from human_approval_workflow import create_plugin as create_approval_plugin  # noqa: E402
from saga_workflow import create_plugin as create_saga_plugin  # noqa: E402
from plain_python_workflow import create_plugin as create_plain_plugin  # noqa: E402
from cobalt_wren.api.plugins import Plugin, PluginContributions, PluginMetadata  # noqa: E402
from cobalt_wren.api.workflow import WorkflowContribution, WorkflowDefinition, WorkflowMetadata, WorkflowRequirements  # noqa: E402
from cobalt_wren.apps.automation.models import Run, Workflow  # noqa: E402
from cobalt_wren.apps.automation.services import runs as run_services  # noqa: E402
from cobalt_wren.apps.automation.services.runtime import build_run_execution_services  # noqa: E402



class DemoTimeoutExecutable:
    def execute(self, input_payload, *, context):
        if context.control is None:
            raise RuntimeError("execution control is required")
        while True:
            context.control.check()
            time.sleep(0.005)


def create_timeout_plugin() -> Plugin:
    contribution = WorkflowContribution(
        kind="demo.timeout",
        definition=WorkflowDefinition(
            kind="demo.timeout",
            metadata=WorkflowMetadata(name="Demo timeout", version="0.1.0"),
            requirements=WorkflowRequirements(),
            build=lambda _context: DemoTimeoutExecutable(),
            extra={"timeout_seconds": 0.02, "lifecycle_events_owner": "control_plane"},
        ),
    )
    return Plugin(
        metadata=PluginMetadata(
            name="ui-demo-timeout",
            version="0.1.0",
            plugin_types=("workflow",),
            provides={"workflows": ("demo.timeout",)},
        ),
        contributions=PluginContributions(workflows=(contribution,)),
    )

PREFIX = "[demo]"
DEMO_ROOT = Path(os.environ.get("COBALT_WREN_UI_DEMO_ROOT", "/tmp/cobalt-wren-ui-demo")).resolve()


def create_run(workflow: Workflow, name: str, payload: dict[str, object]) -> Run:
    return Run.objects.create(workflow=workflow, name=f"{PREFIX} {name}", input_payload=payload)


def main(*, migrate: bool = True) -> None:
    if migrate:
        call_command("migrate", interactive=False, verbosity=0)
    shutil.rmtree(DEMO_ROOT, ignore_errors=True)
    (DEMO_ROOT / "artifacts").mkdir(parents=True, exist_ok=True)
    (DEMO_ROOT / "checkpoints").mkdir(parents=True, exist_ok=True)

    with transaction.atomic():
        Workflow.objects.filter(name__startswith=PREFIX).delete()

    services = build_run_execution_services(
        {
            "version": 1,
            "environment": "ui-demo",
            "stores": {
                "artifact": {"backend": "filesystem", "config": {"root": str(DEMO_ROOT / "artifacts")}},
                "checkpoint": {"backend": "filesystem", "config": {"root": str(DEMO_ROOT / "checkpoints")}},
            },
        },
        plugins=(create_approval_plugin(), create_saga_plugin(), create_plain_plugin(), create_timeout_plugin()),
        discover_plugins=False,
    )

    approval = Workflow.objects.create(
        name=f"{PREFIX} Human approval",
        description="Real pause/resume execution using the external human approval workflow.",
        definition_payload={"workflow": {"kind": "human.approval", "config": {}}},
    )
    saga = Workflow.objects.create(
        name=f"{PREFIX} Order fulfillment saga",
        description="Real parallel partial-failure, retry, and compensation workflow.",
        definition_payload={"workflow": {"kind": "saga.order_fulfillment", "config": {}}},
    )
    plain = Workflow.objects.create(
        name=f"{PREFIX} Plain Python confirmation",
        description="Framework-free external workflow with durable checkpoint resume.",
        definition_payload={"workflow": {"kind": "plain.confirmation", "config": {}}},
    )
    timeout = Workflow.objects.create(
        name=f"{PREFIX} Cooperative timeout",
        description="A cooperative external workflow stopped by the execution deadline.",
        definition_payload={"workflow": {"kind": "demo.timeout", "config": {}}},
    )

    # Pending and cancelled use the same service policies as normal operation.
    create_run(approval, "Pending approval", {"title": "Pending proposal", "proposal": "Not started yet"})
    cancelled = create_run(approval, "Cancelled before start", {"title": "Cancelled proposal", "proposal": "No execution"})
    run_services.cancel_run(run=cancelled, services=services)

    # Waiting approval: start only.
    waiting = create_run(approval, "Waiting for approval", {"title": "Release approval", "proposal": "Deploy version 1.4 to production"})
    run_services.start_run(run=waiting, services=services)

    # Completed approval: start and resume through the public service boundary.
    approved = create_run(approval, "Approved proposal", {"title": "Pricing update", "proposal": "Publish the revised B2B pricing page"})
    started = run_services.start_run(run=approved, services=services)
    run_services.resume_run(run=started.run, resume_payload={"decision": "approve", "note": "Reviewed by operations"}, services=services)

    # Revision loop: a real second pause and checkpoint generation.
    revised = create_run(approval, "Waiting after revision", {"title": "Contract wording", "proposal": "Initial contract wording"})
    started = run_services.start_run(run=revised, services=services)
    run_services.resume_run(run=started.run, resume_payload={"decision": "revise", "proposal": "Revised contract wording with liability cap", "note": "Please review again"}, services=services)

    # Failed run: invalid runtime input is normalized by the execution service.
    failed = create_run(approval, "Failed validation", {"title": "Missing proposal"})
    run_services.start_run(run=failed, services=services)

    # Framework-free waiting run, resumable through the generic UI projection.
    plain_waiting = create_run(plain, "Plain Python waiting", {"subject": "Framework boundary", "message": "Confirm from the generic UI"})
    run_services.start_run(run=plain_waiting, services=services)

    # Cooperative timeout through the real execution-control path.
    timed_out = create_run(timeout, "Timed out cooperatively", {})
    run_services.start_run(run=timed_out, services=services)

    # Saga success.
    completed_saga = create_run(saga, "Saga completed", {"order_id": "DEMO-ORD-1001"})
    run_services.start_run(run=completed_saga, services=services)

    # Saga waiting on a retryable partial failure.
    retryable = create_run(saga, "Saga waiting for retry", {"order_id": "DEMO-ORD-1002", "failure_plan": {"charge_payment": "retryable"}})
    run_services.start_run(run=retryable, services=services)

    # Saga compensation through resume.
    compensated = create_run(saga, "Saga compensated", {"order_id": "DEMO-ORD-1003", "failure_plan": {"provision_access": "fatal"}})
    started = run_services.start_run(run=compensated, services=services)
    run_services.resume_run(run=started.run, resume_payload={"action": "compensate"}, services=services)

    print("UI demo data created through control-plane services.")
    print(f"Workflows: {Workflow.objects.filter(name__startswith=PREFIX).count()}")
    print(f"Runs: {Run.objects.filter(name__startswith=PREFIX).count()}")
    print(f"Artifacts: {sum(run.artifacts.count() for run in Run.objects.filter(name__startswith=PREFIX))}")
    print(f"Checkpoints: {sum(run.checkpoint_metadata.count() for run in Run.objects.filter(name__startswith=PREFIX))}")
    print(f"Runtime bodies: {DEMO_ROOT}")
    print("Open: http://127.0.0.1:8000/ui/runs/")


if __name__ == "__main__":
    main()
