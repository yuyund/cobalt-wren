"""Clean-room wheel, entry-point, Django persistence, and UI proof."""

from __future__ import annotations

import json
import os
from pathlib import Path
import site
import subprocess
import sys


def test_external_oss_distribution_discovers_executes_and_renders(
    tmp_path: Path,
) -> None:
    repo = Path(__file__).resolve().parents[3]
    external = (
        repo
        / "tests"
        / "external_distributions"
        / "oss_integration_workflows"
    )
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()
    for package in (repo, external):
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "wheel",
                "--no-deps",
                "--wheel-dir",
                str(wheelhouse),
                str(package),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

    venv = tmp_path / "venv"
    subprocess.run(
        [sys.executable, "-m", "venv", "--system-site-packages", str(venv)],
        check=True,
    )
    python = venv / "bin" / "python"
    wheels = sorted(wheelhouse.glob("*.whl"))
    subprocess.run(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--no-deps",
            *(str(wheel) for wheel in wheels),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    database = tmp_path / "clean-room.sqlite3"
    script = r'''
import json
from importlib import metadata

import django
from django.core.management import call_command
from django.test import Client

django.setup()

from cobalt_wren.apps.automation.models import (
    ExecutionSpan,
    IntegrationProjectionRecord,
    Run,
    Workflow,
)
from cobalt_wren.apps.automation.services.runs import start_run
from cobalt_wren.apps.automation.services.runtime import (
    build_run_execution_services,
)

call_command("migrate", interactive=False, verbosity=0)
entries = metadata.entry_points().select(group="cobalt_wren.plugins")
services = build_run_execution_services(
    {"version": 1, "environment": "test"},
    discover_plugins=True,
)
results = []
for kind, framework, schema in (
    ("external.oss.langgraph", "LangGraph", "langgraph.task.v1"),
    (
        "external.oss.llamaindex",
        "LlamaIndex Workflows",
        "llamaindex.step.v1",
    ),
):
    workflow = Workflow.objects.create(
        name=f"Clean room {framework}",
        definition_payload={"workflow": {"kind": kind}},
    )
    run = Run.objects.create(
        workflow=workflow,
        name=f"Clean room {framework} run",
        input_payload={"message": f"hello from {framework}"},
    )
    completed = start_run(run=run, services=services).run
    html = Client().get(f"/ui/runs/{completed.pk}/").content.decode()
    results.append(
        {
            "kind": kind,
            "status": completed.status,
            "span_count": ExecutionSpan.objects.filter(run=completed).count(),
            "projection_count": IntegrationProjectionRecord.objects.filter(
                run=completed
            ).count(),
            "schema_present": IntegrationProjectionRecord.objects.filter(
                run=completed,
                schema_id=schema,
            ).exists(),
            "current_state": 'data-component="integration.current-state"' in html,
            "timeline": 'data-component="integration.timeline"' in html,
            "integration_summary": 'data-component="integration.summary"' in html,
        }
    )
print(
    json.dumps(
        {
            "distributions": sorted(
                dist.metadata["Name"] for dist in metadata.distributions()
            ),
            "entry_points": sorted(entry.name for entry in entries),
            "results": results,
        }
    )
)
'''
    env = dict(os.environ)
    env.update(
        {
            "DJANGO_SETTINGS_MODULE": "cobalt_wren.config.settings",
            "DATABASE_URL": f"sqlite:///{database}",
            "PYTHONPATH": os.pathsep.join(site.getsitepackages()),
        }
    )
    completed = subprocess.run(
        [str(python), "-c", script],
        check=True,
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env=env,
    )
    payload = json.loads(completed.stdout.strip())
    assert "cobalt-wren" in payload["distributions"]
    assert "oss-integration-workflows" in payload["distributions"]
    assert "oss-integrations" in payload["entry_points"]
    assert len(payload["results"]) == 2
    for result in payload["results"]:
        assert result["status"] == "succeeded"
        assert result["span_count"] >= 3
        assert result["projection_count"] >= 4
        assert result["schema_present"] is True
        assert result["current_state"] is True
        assert result["timeline"] is True
        assert result["integration_summary"] is True
