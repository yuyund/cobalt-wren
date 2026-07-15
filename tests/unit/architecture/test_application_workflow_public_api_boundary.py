"""Architecture guard for application workflow public API boundaries."""

from __future__ import annotations

from pathlib import Path

from tests.support.import_scan import collect_import_targets


def test_application_workflow_packages_do_not_import_control_plane_or_package_internals() -> None:
    root = Path("src/langgraph_automation/workflows/applications")
    if not root.exists():
        return

    forbidden_prefixes = (
        "langgraph_automation.apps.automation",
        "django",
        "django.conf",
        "django.db",
        "langgraph_automation.plugins.registry",
        "langgraph_automation.runtime.assembly",
        "langgraph_automation.runtime.dependencies",
        "langgraph_automation.config.validator",
        "langgraph_automation.workflows.catalog",
        "langgraph_automation.workflows.prepare",
        "langgraph_automation.workflows.adapter",
        "langgraph_automation.workflows.requirements",
    )

    offenders: list[str] = []
    for path in root.rglob("*.py"):
        modules = collect_import_targets(path)
        for module in modules:
            if module.startswith(forbidden_prefixes):
                offenders.append(f"{path}:{module}")
                break

    assert offenders == [], f"application workflow package imports forbidden modules: {offenders}"
