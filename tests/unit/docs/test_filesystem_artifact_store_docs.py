"""Docs coverage for the filesystem artifact store contract."""

from __future__ import annotations

from pathlib import Path


def test_filesystem_artifact_store_contract_docs_exist_and_cover_core_terms() -> None:
    root = Path('docs')
    contract_index = root / 'contracts' / 'integrations' / 'index.md'
    contract = root / 'contracts' / 'integrations' / 'FILESYSTEM_ARTIFACT_STORE.md'
    design = root / 'architecture' / 'design' / 'DURABLE_ARTIFACT_BACKEND_DESIGN.md'
    audit = root / 'architecture' / 'audit' / 'ARTIFACT_STORE_PROTOCOL_SUFFICIENCY_AUDIT.md'
    test_plan = root / 'assurance' / 'testing' / 'DURABLE_ARTIFACT_TEST_PLAN.md'
    roadmap = root / 'roadmap' / 'milestones' / 'ROADMAP.md'

    for path in (contract_index, contract, design, audit, test_plan, roadmap):
        assert path.exists()

    contract_text = contract.read_text().lower()
    design_text = design.read_text().lower()
    audit_text = audit.read_text().lower()
    test_plan_text = test_plan.read_text().lower()
    roadmap_text = roadmap.read_text().lower()

    for token in (
        'filesystem artifact store contract',
        'process-durable',
        'immutable',
        'idempotent',
        'conflict-aware',
        'integrity-verifying',
        'body-first, manifest-second',
        'sha256(body)',
        'sha256(normalized_storage_key)',
        'deterministic json',
        'artifactintegrityerror',
        'artifactconflicterror',
        'runtime backend selection is deferred',
        'body/metadata orchestration is deferred',
    ):
        assert token in contract_text

    for token in (
        'filesystemartifactstore',
        'implemented',
        'default backend remains memory-backed',
    ):
        assert token in design_text

    for token in (
        'filesystemartifactstore',
        'approved_for_implementation',
        'backend implementation now exists',
        'default backend remains memory-backed',
    ):
        assert token in audit_text

    for token in (
        'filesystem backend is implemented',
        'baseline suite passes for memory and filesystem',
        'advanced durable contract suite passes for filesystem',
        'default backend remains memory',
    ):
        assert token in test_plan_text

    assert 'filesystemartifactstore implementation: complete' in roadmap_text
