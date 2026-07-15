"""Architecture guard for the apps/automation package boundary."""

from __future__ import annotations

from pathlib import Path

from tests.support.import_scan import collect_import_targets

BRIDGE = Path("src/langgraph_automation/apps/automation/services/workflow_preparation.py")


def test_workflow_preparation_bridge_imports_only_the_package_facing_engine_facade() -> None:
    modules = collect_import_targets(BRIDGE)

    forbidden_prefixes = (
        "langgraph_automation.workflows.prepare",
        "langgraph_automation.workflows.catalog",
        "langgraph_automation.workflows.adapter",
        "langgraph_automation.workflows.requirements",
        "langgraph_automation.plugins.registry",
        "langgraph_automation.runtime.assembly",
        "langgraph_automation.runtime.dependencies",
        "langgraph_automation.config.validator",
        "langgraph_automation.graphs",
    )
    offenders = [module for module in modules if module.startswith(forbidden_prefixes)]
    assert offenders == [], f"{BRIDGE} imports forbidden modules: {offenders}"

    for expected in (
        "langgraph_automation.api.engine",
        "langgraph_automation.api.plugins",
    ):
        assert expected in modules
