from __future__ import annotations

from pathlib import Path
import runpy

import pytest

from langgraph_automation.apps.automation.models import Run, RunStatus, Workflow


@pytest.mark.django_db(transaction=True)
def test_ui_demo_seed_uses_real_run_services(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    script = Path(__file__).parents[3] / "scripts" / "seed_ui_demo.py"
    monkeypatch.setenv("LANGGRAPH_AUTOMATION_UI_DEMO_ROOT", str(tmp_path / "ui-runtime"))
    namespace = runpy.run_path(str(script), run_name="ui_demo_seed_test")
    namespace["main"](migrate=False)

    runs = Run.objects.filter(name__startswith="[demo]")
    assert Workflow.objects.filter(name__startswith="[demo]").count() == 2
    assert runs.count() == 9
    assert set(runs.values_list("status", flat=True)) >= {
        RunStatus.PENDING,
        RunStatus.WAITING,
        RunStatus.SUCCEEDED,
        RunStatus.FAILED,
        RunStatus.CANCELLED,
    }
    assert sum(run.events.count() for run in runs) > 0
    assert sum(run.spans.count() for run in runs) > 0
    assert sum(run.artifacts.count() for run in runs) >= 2
    assert sum(run.checkpoint_metadata.count() for run in runs) >= 5
    completed = runs.get(name="[demo] Saga completed")
    assert completed.status == RunStatus.SUCCEEDED
    assert completed.output_payload["summary"]["preview"]["status"] == "completed"
