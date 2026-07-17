"""Docs coverage for checkpoint store protocol sufficiency audit material."""

from __future__ import annotations

from pathlib import Path


def test_checkpoint_store_protocol_sufficiency_docs_exist_and_cover_core_terms() -> None:
    root = Path('docs')
    audit = root / 'architecture' / 'audit' / 'CHECKPOINT_STORE_PROTOCOL_SUFFICIENCY_AUDIT.md'
    design = root / 'architecture' / 'design' / 'DURABLE_CHECKPOINT_BACKEND_DESIGN.md'
    test_plan = root / 'assurance' / 'testing' / 'DURABLE_CHECKPOINT_TEST_PLAN.md'
    contract = root / 'assurance' / 'contracts' / 'PERSISTENCE_DURABILITY_CONTRACT.md'
    traceability = root / 'assurance' / 'testing' / 'PERSISTENCE_TEST_TRACEABILITY.md'
    gaps = root / 'assurance' / 'gaps' / 'PERSISTENCE_DURABILITY_GAPS.md'

    for path in (audit, design, test_plan, contract, traceability, gaps):
        assert path.exists()

    audit_text = audit.read_text().lower()
    design_text = design.read_text().lower()
    test_plan_text = test_plan.read_text().lower()
    contract_text = contract.read_text().lower()
    traceability_text = traceability.read_text().lower()
    gaps_text = gaps.read_text().lower()

    for token in (
        'checkpoint store protocol sufficiency audit',
        'blocked_by_protocol',
        'versioned checkpoint identity',
        'parent / lineage',
        'serializer identity/version',
        'specific-version read',
        'history listing',
        'deterministic latest selection',
        'destructive latest snapshot',
    ):
        assert token in audit_text

    for token in (
        'durable checkpoint backend design',
        'blocked by protocol',
        'request / descriptor / read result separation',
        'immutable checkpoint versions',
        'stable execution identity',
        'process_durable',
        'lineage',
        'specific-version read',
        'history listing',
        'durable checkpoint storage is necessary but not sufficient for true resume',
    ):
        assert token in design_text

    for token in (
        'durable checkpoint test plan',
        'blocked by protocol',
        'current memory checkpoint store uses latest-state replacement by `run_id`',
        'checkpoint protocol evolution is deferred',
        'immutable checkpoint version write',
        'specific-version read',
        'history listing',
        'lost-update detection',
    ):
        assert token in test_plan_text

    for token in (
        '`checkpointstore` is currently a latest-state store keyed by `run_id`',
        '`checkpointstore` sufficiency audit result is `blocked_by_protocol`',
        'current protocol does not express immutable checkpoint versions',
        'specific-version reads',
        'history listing',
        'durable checkpoint implementation remains deferred',
    ):
        assert token in contract_text

    for token in (
        'checkpoint store protocol sufficiency is blocked',
        'missing versioned identity, history, lineage, serializer compatibility, and specific-version reads',
        'checkpoint protocol is blocked',
    ):
        assert token in traceability_text

    for token in (
        'checkpointstore protocol is latest-state only',
        'checkpoint protocol evolution is deferred',
        'recommended closure order',
    ):
        assert token in gaps_text
