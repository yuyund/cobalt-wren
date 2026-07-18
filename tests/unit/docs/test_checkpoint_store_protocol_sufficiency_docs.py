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
        'approved_for_implementation',
        'checkpointwriterequest',
        'storedcheckpoint',
        'checkpointreadresult',
        'parent / lineage',
        'serializer identity/version',
        'specific-version read',
        'history listing',
        'deterministic latest selection',
        'request / descriptor / read-result separation',
    ):
        assert token in audit_text

    for token in (
        'durable checkpoint backend design',
        'approved for implementation',
        'request / descriptor / read-result split',
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
        'approved for implementation',
        'current memory checkpoint store uses linear append-only versioned history',
        'checkpoint protocol evolution is complete',
        'immutable checkpoint version write',
        'specific-version read',
        'history listing',
        'lost-update detection',
    ):
        assert token in test_plan_text

    for token in (
        '`checkpointstore` is a versioned append-only checkpoint repository keyed by `run_id` and `checkpoint_namespace`',
        '`checkpointstore` sufficiency audit result is `approved_for_implementation`',
        'checkpoint_id is caller-issued and identifies an immutable checkpoint version',
        'specific-version reads',
        'history listing',
        'durable checkpoint implementation is now unblocked',
    ):
        assert token in contract_text

    for token in (
        'checkpointstore protocol is versioned and approved for implementation',
        'checkpoint protocol is versioned and approved for implementation',
        'durable backend implementation still deferred',
    ):
        assert token in traceability_text

    for token in (
        'durable checkpoint backend is deferred',
        'checkpoint protocol evolution is complete',
        'recommended closure order',
    ):
        assert token in gaps_text
