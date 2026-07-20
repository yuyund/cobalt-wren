"""Docs coverage for the persistence orchestration sufficiency audit."""

from __future__ import annotations

from pathlib import Path


def test_persistence_orchestration_audit_docs_exist_and_cover_core_terms() -> None:
    root = Path('docs')
    audit = root / 'architecture' / 'audit' / 'PERSISTENCE_ORCHESTRATION_SUFFICIENCY_AUDIT.md'
    audit_index = root / 'architecture' / 'audit' / 'index.md'
    roadmap = root / 'roadmap' / 'milestones' / 'ROADMAP.md'
    traceability = root / 'assurance' / 'testing' / 'PERSISTENCE_TEST_TRACEABILITY.md'
    gaps = root / 'assurance' / 'gaps' / 'PERSISTENCE_DURABILITY_GAPS.md'

    for path in (audit, audit_index, roadmap, traceability, gaps):
        assert path.exists()

    audit_text = audit.read_text().lower()
    audit_index_text = audit_index.read_text().lower()
    roadmap_text = roadmap.read_text().lower()
    traceability_text = traceability.read_text().lower()
    gaps_text = gaps.read_text().lower()

    for token in (
        'persistence orchestration sufficiency audit',
        'canonical production execution call graph',
        'runtime dependency propagation',
        'run lifecycle matrix',
        'artifact ownership and identity',
        'explicit artifact emission only',
        'package-internal emission contract',
        'caller-owned serialization',
        'package-runtime-owned store calls',
        'installed langgraph checkpointer api inventory',
        'checkpoint adapter compatibility matrix',
        'control-plane safe projection',
        'needs_internal_orchestration_contract',
        'blocked_by_pending_writes_contract',
        'blocked_by_run_thread_mapping',
        'blocked_by_control_plane_schema',
        'option_2_required',
        'requires_namespace_policy',
        'execution-owned `run_id`',
        'attempt identifiers are excluded',
        'initial artifact emission policy is required-only',
    ):
        assert token in audit_text

    assert 'persistence_orchestration_sufficiency_audit.md' in audit_index_text
    assert 'persistence orchestration sufficiency audit x1' in roadmap_text
    assert 'execution persistence orchestration is still absent from the production execution path' in traceability_text
    assert 'internal/plugin boundary ambiguity is closed' in gaps_text
