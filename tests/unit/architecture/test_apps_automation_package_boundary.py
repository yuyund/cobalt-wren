"""Architecture guard for the apps/automation package boundary."""

from __future__ import annotations

from pathlib import Path

from tests.support.import_scan import collect_import_targets

APPS_AUTOMATION_ROOT = Path("src/cobalt_wren/apps/automation")

ALLOWED_FORBIDDEN_IMPORTS: dict[Path, set[str]] = {}

FORBIDDEN_PREFIXES = (
    "cobalt_wren.graphs",
    "cobalt_wren.runtime.assembly",
    "cobalt_wren.runtime.dependencies",
    "cobalt_wren.workflows.prepare",
    "cobalt_wren.workflows.catalog",
    "cobalt_wren.workflows.adapter",
    "cobalt_wren.workflows.requirements",
    "cobalt_wren.plugins.registry",
    "cobalt_wren.config.validator",
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
    bridge = Path("src/cobalt_wren/apps/automation/services/workflow_preparation.py")
    modules = collect_import_targets(bridge)

    offenders = [module for module in modules if module.startswith(FORBIDDEN_PREFIXES)]
    assert offenders == [], f"{bridge} imports forbidden modules: {offenders}"

    for expected in (
        "cobalt_wren.api.engine",
        "cobalt_wren.api.plugins",
    ):
        assert expected in modules


def test_no_execution_adapter_requires_an_internal_import_allowlist() -> None:
    assert ALLOWED_FORBIDDEN_IMPORTS == {}
