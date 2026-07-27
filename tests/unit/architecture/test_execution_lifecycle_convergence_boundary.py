"""Guards for the staged Django/public-executable lifecycle convergence."""
from __future__ import annotations
from pathlib import Path
from tests.support.import_scan import collect_import_targets


def test_public_execution_adapter_uses_engine_facade_not_workflow_internals() -> None:
    modules = collect_import_targets(
        Path("src/cobalt_wren/apps/automation/services/execution.py")
    )
    assert "cobalt_wren.api.engine" in modules
    forbidden = (
        "cobalt_wren.workflows.prepare",
        "cobalt_wren.workflows.adapter",
        "cobalt_wren.runtime.assembly",
        "cobalt_wren.runtime.dependencies",
        "cobalt_wren.plugins.registry",
    )
    assert not any(module.startswith(forbidden) for module in modules)


def test_run_service_does_not_prepare_plugins_or_workflows_directly() -> None:
    modules = collect_import_targets(
        Path("src/cobalt_wren/apps/automation/services/runs.py")
    )
    forbidden = (
        "cobalt_wren.workflows",
        "cobalt_wren.plugins.registry",
        "cobalt_wren.runtime.assembly",
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
