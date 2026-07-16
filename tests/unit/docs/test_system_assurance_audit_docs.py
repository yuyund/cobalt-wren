"""Docs coverage for the system assurance audit."""

from __future__ import annotations

from pathlib import Path


def test_system_assurance_audit_docs_exist_and_cover_core_terms() -> None:
    root = Path("docs")
    scope = root / "assurance" / "scope" / "SYSTEM_ASSURANCE_SCOPE.md"
    audit = root / "architecture" / "audit" / "SYSTEM_BOUNDARY_AND_DATAFLOW_AUDIT.md"
    gaps = root / "assurance" / "gaps" / "SYSTEM_ASSURANCE_GAPS.md"
    roadmap = root / "roadmap" / "milestones" / "ROADMAP.md"

    for path in (scope, audit, gaps):
        assert path.exists()

    scope_text = scope.read_text()
    audit_text = audit.read_text()
    gaps_text = gaps.read_text()
    roadmap_text = roadmap.read_text()

    haystack = "\n".join((scope_text, audit_text, gaps_text))
    for token in (
        "code is the source of truth",
        "tests are the source of truth",
        "supplemental report is hypothesis only",
        "PluginResolutionError",
        "execution-adapter boundary",
        "Layer / Dependency Matrix",
        "Dataflow Matrix",
        "Lifecycle Matrix",
        "Safety Matrix",
        "Error Matrix",
        "Persistence Matrix",
        "UI Exposure Matrix",
        "Observability Matrix",
        "Extension Matrix",
        "P0",
        "P1",
        "P2",
    ):
        assert token.lower() in haystack.lower()

    assert "system assurance scope expansion audit block q" in roadmap_text.lower()
    assert "system p0 assurance gap closure block r" in roadmap_text.lower()
    assert "system p1 safety exposure hardening block s" in roadmap_text.lower()
    assert "admin/ui redaction assurance" in roadmap_text.lower()
