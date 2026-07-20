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
        'package-internal contract',
        'external plugin import is unsupported',
        'artifactemissionrequest',
        'artifactidentity',
        'artifactslot',
        'artifactoccurrence',
        'run_id + slot + occurrence',
        'execution-owned `run_id`',
        'attempt identifiers are excluded',
        'caller-owned serialization',
        'bounded logical json',
        'required-only policy',
        'deeply immutable metadata normalization',
        'deterministic internal mapping to `artifactwriterequest`',
        'same run / same logical artifact -> same identity',
        'new run / rerun -> different identity',
        'artifactstore.put is still not connected to production execution',
    ):
        assert token in contract_text

    for token in (
        'explicit artifact emission only',
        'caller-owned serialization',
        'package-runtime-owned store calls',
        'package-internal emission contract',
        'artifact ownership and identity',
    ):
        assert token in audit_text

    for token in (
        'artifact emission contract is explicit-only',
        'artifact emission is explicit-only, package-internal, and logical identity is run + slot + occurrence',
        'artifact identity is deterministic',
        'production artifactstore.put callers remain zero',
        'execution-owned `run_id`',
        'required-only policy',
    ):
        assert token in traceability_text

    for token in (
        'artifact logical identity ambiguity',
        'retry identity ambiguity',
        'slot/occurrence ambiguity',
        'serialization ownership ambiguity',
        'internal/plugin boundary ambiguity is closed',
        'producer-controlled run_id ambiguity is closed',
        'attempt identity ambiguity is closed',
        'optional policy ambiguity is closed',
        'request equivalence ambiguity is closed',
        'validation bounds ambiguity is closed',
        'metadata boundedness ambiguity is closed',
        'deterministic write mapping ambiguity is closed',
    ):
        assert token in gaps_text

    for token in (
        'artifact emission and identity contract x2',
        'status: complete',
        'next block: artifact persistence orchestration implementation x4',
        'artifact emission contract completeness closure x2a',
        'package-internal contract: complete',
    ):
        assert token in roadmap_text

    for token in (
        'artifactemissionrequest',
        'artifactidentity',
        'artifactslot',
        'artifactoccurrence',
        'package-internal',
        'provisional',
        'execution-provided `run_id`',
    ):
        assert token in api_text
