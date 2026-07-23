"""Architecture guard for separately distributed workflow packages."""

from __future__ import annotations

from pathlib import Path

from tests.support.import_scan import collect_import_targets


_EXTERNAL_PACKAGE_ROOT = Path("tests/external_packages/acme_workflows")
_ALLOWED_PACKAGE_IMPORTS = (
    "langgraph_automation.api.plugins",
    "langgraph_automation.api.workflow",
    "langgraph_automation.api.stores",
)


def test_external_workflow_fixture_is_outside_the_foundation_source_tree() -> None:
    source_root = Path("src/langgraph_automation").resolve()

    for path in _EXTERNAL_PACKAGE_ROOT.rglob("*.py"):
        assert not path.resolve().is_relative_to(source_root)


def test_external_workflow_package_imports_only_public_plugin_spi() -> None:
    offenders: list[str] = []

    for path in _EXTERNAL_PACKAGE_ROOT.rglob("*.py"):
        for module in collect_import_targets(path):
            if not module.startswith("langgraph_automation"):
                continue
            if not module.startswith(_ALLOWED_PACKAGE_IMPORTS):
                offenders.append(f"{path}:{module}")

    assert offenders == [], f"external workflow package imports package internals: {offenders}"


def test_external_workflow_package_does_not_import_engine_or_control_plane() -> None:
    forbidden_prefixes = (
        "langgraph_automation.api.engine",
        "langgraph_automation.apps",
        "langgraph_automation.config",
        "langgraph_automation.graphs",
        "langgraph_automation.integrations",
        "langgraph_automation.plugins",
        "langgraph_automation.runtime",
        "langgraph_automation.workflows",
        "django",
    )
    offenders: list[str] = []

    for path in _EXTERNAL_PACKAGE_ROOT.rglob("*.py"):
        for module in collect_import_targets(path):
            if module.startswith(forbidden_prefixes):
                offenders.append(f"{path}:{module}")

    assert offenders == [], f"external workflow package crosses the package boundary: {offenders}"
