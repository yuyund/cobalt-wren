"""Docs coverage for persistence durability audit material."""

from __future__ import annotations

from pathlib import Path


def test_persistence_durability_audit_docs_exist_and_cover_core_terms() -> None:
    root = Path('docs')
    contract = root / 'assurance' / 'contracts' / 'PERSISTENCE_DURABILITY_CONTRACT.md'
    audit = root / 'architecture' / 'audit' / 'PERSISTENCE_FAILURE_MODE_AUDIT.md'
    traceability = root / 'assurance' / 'testing' / 'PERSISTENCE_TEST_TRACEABILITY.md'
    gaps = root / 'assurance' / 'gaps' / 'PERSISTENCE_DURABILITY_GAPS.md'

    for path in (contract, audit, traceability, gaps):
        assert path.exists()

    contract_text = contract.read_text().lower()
    audit_text = audit.read_text().lower()
    traceability_text = traceability.read_text().lower()
    gaps_text = gaps.read_text().lower()

    for token in (
        'metadata / body plane separation',
        'artifact / checkpoint body-vs-metadata separation',
        'durability levels',
        'ephemeral',
        'process_durable',
        'deployment_durable',
        'absent',
        'valid',
        'orphan_body',
        'dangling_metadata',
        'corrupt',
        'immutability',
        'idempotency',
        'integrity',
        'failure-mode matrix',
        'artifact semantics',
        'checkpoint semantics',
        'true resume',
    ):
        assert token in contract_text

    for token in (
        'actual call sites',
        'current write / read flows',
        'buckets: w write failures, r read failures, c retry / concurrency failures, s safety failures, d restart / durability failures.',
        'body-first',
        'metadata-second',
    ):
        assert token in audit_text

    for token in (
        'invariant',
        'implementation point',
        'current test',
        'required test layer',
        'gap',
        'risk',
        'reusable backend contract suite',
        'fault-injection',
        'restart durability',
        'concurrency',
        'safety exposure regression',
        'body-aware',
        'approved_for_implementation',
    ):
        assert token in traceability_text

    for token in (
        'p0',
        'p1',
        'p2',
        'production behavior was not changed',
        'next block',
        'durable artifact/checkpoint backend is deferred',
        'artifactstore protocol evolution is complete',
    ):
        assert token in gaps_text
