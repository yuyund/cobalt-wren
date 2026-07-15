"""Docs coverage for the package assurance audit baseline."""

from __future__ import annotations

from pathlib import Path


def test_package_assurance_audit_docs_exist_and_cover_traceability_terms() -> None:
    root = Path("docs")
    inventory = root / "PACKAGE_ASSURANCE_INVENTORY.md"
    invariants = root / "PACKAGE_INVARIANTS.md"
    traceability = root / "PACKAGE_TEST_TRACEABILITY.md"
    gaps = root / "PACKAGE_ASSURANCE_GAPS.md"
    roadmap = root / "PACKAGE_TEST_ROADMAP.md"
    api_surface = root / "API_SURFACE.md"

    for path in (inventory, invariants, traceability, gaps, roadmap):
        assert path.exists()

    inventory_text = inventory.read_text()
    invariants_text = invariants.read_text()
    traceability_text = traceability.read_text()
    gaps_text = gaps.read_text()
    roadmap_text = roadmap.read_text()
    api_surface_text = api_surface.read_text()

    for token in ("CODE_CONFIRMED", "TEST_CONFIRMED", "ARCH_GUARD_CONFIRMED", "DOC_ONLY", "ASSUMED", "GAP"):
        assert token in inventory_text

    assert "Evidence Levels" in inventory_text
    assert "Boundary Invariants" in invariants_text
    assert "Requirement / Invariant | Implementation point | Current tests | Coverage level | Gap | Risk" in traceability_text
    assert "code is the source of truth" in inventory_text.lower()
    assert "traceability matrix" in traceability_text.lower()
    assert "p0" in gaps_text.lower()
    assert "p1" in gaps_text.lower()
    assert "p2" in gaps_text.lower()
    assert "apps/automation" in gaps_text.lower()
    assert "pluginresolutionerror" in gaps_text.lower()
    assert "exact execution-adapter allowlist" in gaps_text.lower()
    assert "closure order" in roadmap_text.lower()
    assert "unknownworkflowkinderror" not in api_surface_text.lower()
    assert "pluginresolutionerror" in api_surface_text.lower()
