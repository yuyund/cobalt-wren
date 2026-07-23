"""Guards for the audited workflow metadata/UI projection boundary."""

from __future__ import annotations

from pathlib import Path

from tests.support.import_scan import collect_import_targets


def test_public_workflow_vocabulary_is_django_free() -> None:
    modules = collect_import_targets(Path("src/langgraph_automation/api/workflow.py"))
    assert not any(module.startswith("django") for module in modules)
    assert not any(module.startswith("langgraph_automation.apps") for module in modules)


def test_ui_projection_audit_records_current_coupling_and_future_boundary() -> None:
    text = Path("docs/architecture/design/UI_PROJECTION_BOUNDARY_AUDIT.md").read_text()
    assert "Django control-plane renderer" in text
    assert "Generic workflow-to-UI projection adapter: not implemented" in text
    assert "never workflow objects" in text
