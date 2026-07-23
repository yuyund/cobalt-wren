from __future__ import annotations

from pathlib import Path

from tests.support.import_scan import collect_import_targets

ROOT = Path("src/langgraph_automation")


def test_legacy_graph_package_is_absent() -> None:
    assert not (ROOT / "graphs").exists()


def test_django_control_plane_does_not_import_langgraph_framework() -> None:
    offenders: dict[str, list[str]] = {}
    for path in (ROOT / "apps").rglob("*.py"):
        modules = collect_import_targets(path)
        bad = [module for module in modules if module == "langgraph" or module.startswith("langgraph.")]
        if bad:
            offenders[str(path)] = bad
    assert offenders == {}


def test_public_workflow_facade_does_not_expose_framework_types() -> None:
    text = (ROOT / "api" / "workflow.py").read_text(encoding="utf-8")
    assert "from langgraph" not in text
    assert "import langgraph" not in text


def test_reference_workflow_is_the_only_package_area_importing_langgraph() -> None:
    offenders: list[str] = []
    for path in ROOT.rglob("*.py"):
        modules = collect_import_targets(path)
        if any(module == "langgraph" or module.startswith("langgraph.") for module in modules):
            relative = path.relative_to(ROOT).as_posix()
            if not relative.startswith("workflows/reference/"):
                offenders.append(relative)
    assert offenders == []
