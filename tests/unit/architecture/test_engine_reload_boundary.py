"""Architecture and documentation guards for deployment engine reload."""
from __future__ import annotations
from pathlib import Path
from tests.support.import_scan import collect_import_targets


def test_engine_generation_is_control_plane_owned() -> None:
    modules = collect_import_targets(
        Path("src/langgraph_automation/apps/automation/services/runtime.py")
    )
    assert "langgraph_automation.api.engine" in modules
    assert not any(
        module.startswith("langgraph_automation.workflows.prepare") for module in modules
    )


def test_reload_contract_documents_last_known_good_and_process_scope() -> None:
    text = Path(
        "docs/architecture/design/EXECUTION_LIFECYCLE_CONVERGENCE.md"
    ).read_text()
    for phrase in (
        "Engine Cache Generation And Reload",
        "last-known-good",
        "process-local",
        "does not guarantee Python module hot reload",
        "Multi-worker deployments",
    ):
        assert phrase in text
