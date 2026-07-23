"""Architecture guards for automatic execution convergence."""
from __future__ import annotations
from pathlib import Path
from tests.support.import_scan import collect_import_targets


def test_control_plane_result_has_no_graph_dependency() -> None:
    modules = collect_import_targets(
        Path("src/langgraph_automation/apps/automation/services/execution_result.py")
    )
    assert not any(module.startswith("langgraph_automation.graphs") for module in modules)


def test_workflow_reference_parser_has_no_engine_or_graph_dependency() -> None:
    modules = collect_import_targets(
        Path("src/langgraph_automation/apps/automation/services/workflow_reference.py")
    )
    forbidden = ("langgraph_automation.api.engine", "langgraph_automation.graphs")
    assert not any(module.startswith(forbidden) for module in modules)


def test_run_orchestrator_does_not_import_graph_result_type() -> None:
    modules = collect_import_targets(
        Path("src/langgraph_automation/apps/automation/services/runs.py")
    )
    assert "langgraph_automation.graphs.runner" not in modules
    assert "langgraph_automation.apps.automation.services.execution_result" in modules


def test_reference_schema_and_event_ownership_are_documented() -> None:
    text = Path(
        "docs/architecture/design/EXECUTION_LIFECYCLE_CONVERGENCE.md"
    ).read_text()
    for phrase in (
        "Control-plane Workflow Reference",
        "Deployment Engine Ownership",
        "Execution Selection",
        "Framework-neutral Control-plane Result",
        "Lifecycle Event Ownership",
    ):
        assert phrase in text
