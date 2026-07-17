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
        'blocked_by_protocol',
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
        'status: blocked by protocol',
        'immutable checkpoint versions',
        'request / descriptor / read result separation',
        'checkpoint-bodies',
        'heads/',
        'process_durable',
        'orphan body is allowed',
        'durable checkpoint storage is necessary but not sufficient for true resume',
    ):
        assert token in design_text

    for token in (
        'durable checkpoint test plan',
        'status: blocked by protocol',
        'current memory checkpoint store uses latest-state replacement by `run_id`',
        'no durable checkpoint backend implementation is attempted before protocol evolution',
        'specific-version read',
        'history listing',
        'lost-update detection',
    ):
        assert token in test_plan_text

    for token in (
        'checkpoint durability contract and protocol sufficiency audit block w1',
        'blocked_by_protocol',
        'checkpoint protocol sufficiency audit: complete',
        'next block: checkpoint store protocol evolution block w2',
    ):
        assert token in roadmap_text

