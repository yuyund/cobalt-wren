"""Docs coverage for the explicit artifact emission contract."""

from __future__ import annotations

from pathlib import Path


def test_artifact_emission_contract_docs_exist_and_cover_core_terms() -> None:
    root = Path('docs')
    contract = root / 'assurance' / 'contracts' / 'ARTIFACT_EMISSION_CONTRACT.md'
    audit = root / 'architecture' / 'audit' / 'PERSISTENCE_ORCHESTRATION_SUFFICIENCY_AUDIT.md'
    traceability = root / 'assurance' / 'testing' / 'PERSISTENCE_TEST_TRACEABILITY.md'
    gaps = root / 'assurance' / 'gaps' / 'PERSISTENCE_DURABILITY_GAPS.md'
    roadmap = root / 'roadmap' / 'milestones' / 'ROADMAP.md'
    api_surface = root / 'api' / 'surface' / 'API_SURFACE.md'

    for path in (contract, audit, traceability, gaps, roadmap, api_surface):
        assert path.exists()

    contract_text = contract.read_text().lower()
    audit_text = audit.read_text().lower()
    traceability_text = traceability.read_text().lower()
    gaps_text = gaps.read_text().lower()
    roadmap_text = roadmap.read_text().lower()
    api_text = api_surface.read_text().lower()

    for token in (
        'explicit artifact emission only',
        'artifactemissionrequest',
        'artifactidentity',
        'artifactslot',
        'artifactoccurrence',
        'run_id + slot + occurrence',
        'caller-owned serialization',
        'bounded logical json',
        'same run / same logical artifact -> same identity',
        'new run / rerun -> different identity',
        'artifactstore.put is still not connected to production execution',
    ):
        assert token in contract_text

    for token in (
        'explicit artifact emission only',
        'caller-owned serialization',
        'package-runtime-owned store calls',
        'artifact ownership and identity',
    ):
        assert token in audit_text

    for token in (
        'artifact emission contract is explicit-only',
        'artifact identity is deterministic',
        'production artifactstore.put callers remain zero',
    ):
        assert token in traceability_text

    for token in (
        'artifact logical identity ambiguity',
        'retry identity ambiguity',
        'slot/occurrence ambiguity',
        'serialization ownership ambiguity',
    ):
        assert token in gaps_text

    for token in (
        'artifact emission and identity contract x2',
        'status: complete',
        'next block: artifact persistence orchestration implementation x4',
    ):
        assert token in roadmap_text

    for token in (
        'artifactemissionrequest',
        'artifactidentity',
        'artifactslot',
        'artifactoccurrence',
        'internal',
        'provisional',
    ):
        assert token in api_text
