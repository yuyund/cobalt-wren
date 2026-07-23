"""Guards for the staged Django/public-executable lifecycle convergence."""
from __future__ import annotations
from pathlib import Path
from tests.support.import_scan import collect_import_targets


def test_public_execution_adapter_uses_engine_facade_not_workflow_internals() -> None:
    modules = collect_import_targets(
        Path("src/langgraph_automation/apps/automation/services/execution.py")
    )
    assert "langgraph_automation.api.engine" in modules
    forbidden = (
        "langgraph_automation.workflows.prepare",
        "langgraph_automation.workflows.adapter",
        "langgraph_automation.runtime.assembly",
        "langgraph_automation.runtime.dependencies",
        "langgraph_automation.plugins.registry",
    )
    assert not any(module.startswith(forbidden) for module in modules)


def test_run_service_does_not_prepare_plugins_or_workflows_directly() -> None:
    modules = collect_import_targets(
        Path("src/langgraph_automation/apps/automation/services/runs.py")
    )
    forbidden = (
        "langgraph_automation.workflows",
        "langgraph_automation.plugins.registry",
        "langgraph_automation.runtime.assembly",
    )
    assert not any(module.startswith(forbidden) for module in modules)


def test_convergence_design_records_automatic_selection_boundary() -> None:
    text = Path(
        "docs/architecture/design/EXECUTION_LIFECYCLE_CONVERGENCE.md"
    ).read_text()
    assert "Execution Selection" in text
    assert "Run execution does not construct `GraphRuntime`" in text
    assert "Resume remains unsupported" in text
    assert "prepared_workflow=" not in text
