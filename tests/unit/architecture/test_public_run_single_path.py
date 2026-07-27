"""Guards for the public-executable-only Run lifecycle."""

from pathlib import Path

from tests.support.import_scan import collect_import_targets


def test_run_service_has_no_graph_runtime_dependency() -> None:
    modules = collect_import_targets(
        Path("src/cobalt_wren/apps/automation/services/runs.py")
    )
    assert not any(
        module.startswith("cobalt_wren.graphs") for module in modules
    )


def test_execution_adapter_has_no_graph_runner_dependency() -> None:
    modules = collect_import_targets(
        Path("src/cobalt_wren/apps/automation/services/execution.py")
    )
    assert not any(
        module.startswith("cobalt_wren.graphs") for module in modules
    )


def test_builtin_catalog_does_not_supply_product_workflows() -> None:
    text = Path("src/cobalt_wren/workflows/catalog.py").read_text()

    assert "_BUILTIN_WORKFLOW_PLUGINS: tuple[Plugin, ...] = ()" in text
    assert "reference" not in text
    assert "examples" in text
