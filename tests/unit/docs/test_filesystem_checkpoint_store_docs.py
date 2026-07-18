"""Docs coverage for the filesystem checkpoint backend."""

from __future__ import annotations

from pathlib import Path


def test_filesystem_checkpoint_store_docs_exist_and_cover_core_terms() -> None:
    root = Path('docs')
    contract = root / 'contracts' / 'integrations' / 'CHECKPOINT_STORE.md'
    design = root / 'architecture' / 'design' / 'DURABLE_CHECKPOINT_BACKEND_DESIGN.md'
    test_plan = root / 'assurance' / 'testing' / 'DURABLE_CHECKPOINT_TEST_PLAN.md'
    roadmap = root / 'roadmap' / 'milestones' / 'ROADMAP.md'

    for path in (contract, design, test_plan, roadmap):
        assert path.exists()

    contract_text = contract.read_text().lower()
    design_text = design.read_text().lower()
    test_plan_text = test_plan.read_text().lower()
    roadmap_text = roadmap.read_text().lower()

    for token in (
        'filesystemcheckpointstore',
        'process_durable',
        'immutable body publication',
        'immutable checkpoint record publication',
        'mutable head advancement',
        'pending append intent',
        'crash-window recovery',
        'checkpoint runtime selection is implemented through typed config and the canonical builder',
        'runtime/composition work is execution persistence orchestration',
    ):
        assert token in contract_text

    for token in (
        'filesystem layout',
        'bodies/',
        'streams/',
        'head.json',
        'pending.json',
        'records/by-id',
        'records/by-revision',
        'process_durable',
        'same host',
        'same filesystem root',
        'orphan body is allowed',
        'orphan checkpoint record is allowed',
        'impossible combinations raise `checkpointintegrityerror`',
    ):
        assert token in design_text

    for token in (
        'filesystem backend is implemented',
        'baseline suite passes for memory and filesystem',
        'advanced durable contract suite passes for filesystem',
        'default backend remains memory',
        'filesystem runtime selection is explicit opt-in and typed',
    ):
        assert token in test_plan_text

    for token in (
        'filesystem checkpoint backend implementation: complete',
        'process-durable filesystem checkpoint backend: complete',
        'checkpoint backend runtime selection and configuration block w4',
    ):
        assert token in roadmap_text
