"""Docs coverage for the artifact store protocol evolution block."""

from __future__ import annotations

from pathlib import Path


def test_artifact_store_protocol_evolution_docs_exist_and_cover_core_terms() -> None:
    root = Path('docs')
    protocol_audit = root / 'architecture' / 'audit' / 'ARTIFACT_STORE_PROTOCOL_SUFFICIENCY_AUDIT.md'
    design = root / 'architecture' / 'design' / 'DURABLE_ARTIFACT_BACKEND_DESIGN.md'
    test_plan = root / 'assurance' / 'testing' / 'DURABLE_ARTIFACT_TEST_PLAN.md'
    api_surface = root / 'api' / 'surface' / 'API_SURFACE.md'
    contracts = root / 'contracts' / 'core' / 'CONTRACTS.md'

    for path in (protocol_audit, design, test_plan, api_surface, contracts):
        assert path.exists()

    protocol_text = protocol_audit.read_text().lower()
    design_text = design.read_text().lower()
    test_plan_text = test_plan.read_text().lower()
    api_text = api_surface.read_text().lower()
    contracts_text = contracts.read_text().lower()

    for token in (
        'approved_for_implementation',
        'artifactwriterequest',
        'storedartifact',
        'artifactreadresult',
        'body-aware',
        'immutable',
        'idempotent',
        'conflict-aware',
        'filesystemartifactstore',
        'default backend remains memory',
    ):
        assert token in protocol_text

    for token in (
        'protocol is now protocol-sufficient',
        'metadata / body separation',
        'temp file + hard-link publication',
        'safe errors',
        'filesystemartifactstore',
        'default backend remains memory-backed',
    ):
        assert token in design_text

    for token in (
        'body round-trip',
        'deterministic list ordering',
        'idempotent write',
        'conflict detection',
        'size correctness',
        'digest correctness',
        'repr safety',
        'protocol sufficiency is approved for implementation',
    ):
        assert token in test_plan_text

    for token in (
        'artifactwriterequest',
        'storedartifact',
        'artifactreadresult',
        'provisional breaking revision',
        'body-aware breaking revision',
    ):
        assert token in api_text

    for token in (
        'body is bytes',
        'request / descriptor / read result are separated',
        'immutable write',
        'idempotent write',
        'conflict detection',
        'size and digest are store-derived',
    ):
        assert token in contracts_text
