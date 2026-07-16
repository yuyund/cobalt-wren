"""Docs coverage for durable artifact backend design and protocol sufficiency."""

from __future__ import annotations

from pathlib import Path


def test_durable_artifact_backend_design_docs_exist_and_cover_core_terms() -> None:
    root = Path('docs')
    protocol_audit = root / 'architecture' / 'audit' / 'ARTIFACT_STORE_PROTOCOL_SUFFICIENCY_AUDIT.md'
    design = root / 'architecture' / 'design' / 'DURABLE_ARTIFACT_BACKEND_DESIGN.md'
    test_plan = root / 'assurance' / 'testing' / 'DURABLE_ARTIFACT_TEST_PLAN.md'

    for path in (protocol_audit, design, test_plan):
        assert path.exists()

    protocol_text = protocol_audit.read_text().lower()
    design_text = design.read_text().lower()
    test_plan_text = test_plan.read_text().lower()

    for token in (
        'blocked_by_protocol',
        'process_durable',
        'filesystemartifactstore',
        'metadata-only',
        'body input',
        'body output',
        'idempotency',
        'integrity',
        'protocol evolution options',
        'recommended path: `b`',
        'default backend remains memory',
    ):
        assert token in protocol_text

    for token in (
        'durable artifact backend design',
        'filesystemartifactstore',
        'process_durable',
        'metadata / body separation',
        'temp file + hard-link publication',
        'immutable no-overwrite publication',
        'same-key/same-content',
        'same-key/different-content',
        'restart and concurrency',
        'safe errors',
        'protocol dependency',
        'default backend remains memoryartifactstore',
    ):
        assert token in design_text

    for token in (
        'baseline contract activation',
        'advanced contract activation',
        'restart test',
        'corruption test',
        'missing body test',
        'same-key/same-content test',
        'same-key/different-content test',
        'two-instance concurrency test',
        'process concurrency test',
        'safe error test',
        'path/symlink test',
        'backend registration test',
        'runtime wiring test',
        'xfail policy',
        'default backend remains memory',
        'checkpoint durability is deferred',
        'body/metadata orchestration is deferred',
        'true resume is deferred',
    ):
        assert token in test_plan_text
