"""Architecture guard for application workflow public API boundaries."""

from __future__ import annotations

from pathlib import Path

from tests.support.import_scan import collect_import_targets


def test_application_workflow_packages_do_not_import_control_plane_or_package_internals() -> None:
    root = Path("src/cobalt_wren/workflows/applications")
    if not root.exists():
        return

    forbidden_prefixes = (
        "cobalt_wren.apps.automation",
        "django",
        "django.conf",
        "django.db",
        "cobalt_wren.plugins.registry",
        "cobalt_wren.runtime.assembly",
        "cobalt_wren.runtime.dependencies",
        "cobalt_wren.config.validator",
        "cobalt_wren.workflows.catalog",
        "cobalt_wren.workflows.prepare",
        "cobalt_wren.workflows.adapter",
        "cobalt_wren.workflows.requirements",
    )

    offenders: list[str] = []
    for path in root.rglob("*.py"):
        modules = collect_import_targets(path)
        for module in modules:
            if module.startswith(forbidden_prefixes):
                offenders.append(f"{path}:{module}")
                break

    assert offenders == [], f"application workflow package imports forbidden modules: {offenders}"
