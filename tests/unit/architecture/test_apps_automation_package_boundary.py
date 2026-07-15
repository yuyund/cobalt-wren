"""Architecture guard for the apps/automation package boundary."""

from __future__ import annotations

from pathlib import Path

from tests.support.import_scan import collect_import_targets

APPS_AUTOMATION_ROOT = Path("src/langgraph_automation/apps/automation")

ALLOWED_FORBIDDEN_IMPORTS = {
    Path("src/langgraph_automation/apps/automation/services/runtime.py"): {
        "langgraph_automation.graphs.config",
        "langgraph_automation.graphs.registry",
        "langgraph_automation.graphs.runtime",
        "langgraph_automation.workflows.catalog",
    },
    Path("src/langgraph_automation/apps/automation/services/execution.py"): {
        "langgraph_automation.graphs.runner",
        "langgraph_automation.graphs.runtime",
    },
    Path("src/langgraph_automation/apps/automation/services/runs.py"): {
        "langgraph_automation.graphs.runner",
        "langgraph_automation.graphs.runtime",
    },
}

FORBIDDEN_PREFIXES = (
    "langgraph_automation.graphs",
    "langgraph_automation.runtime.assembly",
    "langgraph_automation.runtime.dependencies",
    "langgraph_automation.workflows.prepare",
    "langgraph_automation.workflows.catalog",
    "langgraph_automation.workflows.adapter",
    "langgraph_automation.workflows.requirements",
    "langgraph_automation.plugins.registry",
    "langgraph_automation.config.validator",
)


def test_apps_automation_package_does_not_import_package_internals_outside_exact_execution_adapters() -> None:
    offenders: list[str] = []

    for path in APPS_AUTOMATION_ROOT.rglob("*.py"):
        modules = collect_import_targets(path)
        allowed_for_path = ALLOWED_FORBIDDEN_IMPORTS.get(path, set())
        for module in modules:
            is_allowed = any(module == allowed or module.startswith(f"{allowed}.") for allowed in allowed_for_path)
            if module.startswith(FORBIDDEN_PREFIXES) and not is_allowed:
                offenders.append(f"{path}:{module}")

    assert offenders == [], f"apps/automation imports forbidden package internals outside exact execution adapters: {offenders}"


def test_workflow_preparation_bridge_imports_only_the_package_facing_engine_facade() -> None:
    bridge = Path("src/langgraph_automation/apps/automation/services/workflow_preparation.py")
    modules = collect_import_targets(bridge)

    offenders = [module for module in modules if module.startswith(FORBIDDEN_PREFIXES)]
    assert offenders == [], f"{bridge} imports forbidden modules: {offenders}"

    for expected in (
        "langgraph_automation.api.engine",
        "langgraph_automation.api.plugins",
    ):
        assert expected in modules


def test_execution_adapters_have_exact_graph_runtime_allowlist() -> None:
    for path, allowed in ALLOWED_FORBIDDEN_IMPORTS.items():
        modules = collect_import_targets(path)
        offenders = [
            module
            for module in modules
            if module.startswith(FORBIDDEN_PREFIXES)
            and not any(module == allowed_prefix or module.startswith(f"{allowed_prefix}.") for allowed_prefix in allowed)
        ]
        assert offenders == [], f"{path} imports forbidden modules outside its exact allowlist: {offenders}"
