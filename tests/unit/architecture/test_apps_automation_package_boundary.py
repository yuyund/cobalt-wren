"""Architecture guard for the transitional apps/automation package boundary."""

from __future__ import annotations

from pathlib import Path

from tests.support.import_scan import collect_import_targets

TEMPORARY_EXCEPTION = Path("src/langgraph_automation/apps/automation/services/workflow_preparation.py")


def test_workflow_preparation_bridge_is_the_only_temporary_exception() -> None:
    """Temporary exception: keep this exact bridge until Service Integration via Package Facade Block O."""
    modules = collect_import_targets(TEMPORARY_EXCEPTION)

    forbidden_prefixes = (
        "langgraph_automation.workflows.reference",
        "langgraph_automation.graphs.runner",
        "langgraph_automation.graphs.builders",
        "langgraph_automation.config.validator",
        "langgraph_automation.runtime.assembly",
    )
    offenders = [module for module in modules if module.startswith(forbidden_prefixes)]
    assert offenders == [], f"{TEMPORARY_EXCEPTION} imports forbidden modules: {offenders}"

    expected_prefixes = (
        "langgraph_automation.workflows.prepare",
        "langgraph_automation.workflows.catalog",
        "langgraph_automation.runtime.dependencies",
        "langgraph_automation.plugins.registry",
        "langgraph_automation.api.errors",
    )
    assert any(module.startswith(expected_prefixes) for module in modules)
