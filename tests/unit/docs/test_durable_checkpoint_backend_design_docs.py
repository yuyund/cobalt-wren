"""Docs coverage for durable checkpoint backend design and acceptance planning."""

from __future__ import annotations

from pathlib import Path


def test_durable_checkpoint_backend_design_docs_exist_and_cover_core_terms() -> None:
    root = Path('docs')
    audit = root / 'architecture' / 'audit' / 'CHECKPOINT_STORE_PROTOCOL_SUFFICIENCY_AUDIT.md'
    design = root / 'architecture' / 'design' / 'DURABLE_CHECKPOINT_BACKEND_DESIGN.md'
    test_plan = root / 'assurance' / 'testing' / 'DURABLE_CHECKPOINT_TEST_PLAN.md'
    roadmap = root / 'roadmap' / 'milestones' / 'ROADMAP.md'

    for path in (audit, design, test_plan, roadmap):
        assert path.exists()

    audit_text = audit.read_text().lower()
    design_text = design.read_text().lower()
    test_plan_text = test_plan.read_text().lower()
    roadmap_text = roadmap.read_text().lower()

    for token in (
        'approved_for_implementation',
        'checkpoint store contract',
        'versioned checkpoint identity',
        'specific-version read',
        'history listing',
        'serializer identity/version',
        'deterministic latest selection',
        'parent / lineage',
        'option b',
    ):
        assert token in audit_text

    for token in (
        'durable checkpoint backend design',
        'status: implemented and approved for implementation',
        'immutable checkpoint versions',
        'request / descriptor / read-result split',
        'bodies/',
        'streams/',
        'head.json',
        'pending.json',
        'lock',
        'process_durable',
        'orphan body is allowed',
        'same host',
        'durable checkpoint storage is necessary but not sufficient for true resume',
        'lossless logical json value',
        'filesystem checkpoint backend is now implemented',
        'checkpoint runtime selection is implemented through typed config and the canonical builder',
    ):
        assert token in design_text

    for token in (
        'durable checkpoint test plan',
        'status: implemented and approved for implementation',
        'current memory checkpoint store uses linear append-only versioned history',
        'current filesystem checkpoint store is process_durable',
        'filesystem backend is implemented',
        'specific-version read',
        'history listing',
        'lost-update detection',
        'metadata fidelity',
        'filesystem runtime selection is explicit opt-in and typed',
    ):
        assert token in test_plan_text

    for token in (
        'checkpoint durability contract and protocol sufficiency audit block w1',
        'approved_for_implementation',
        'checkpoint store protocol evolution block w2',
        'filesystem checkpoint backend implementation block w3',
        'next block: checkpoint backend runtime selection and configuration block w4',
    ):
        assert token in roadmap_text
