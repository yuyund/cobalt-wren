"""Docs coverage for application workflow readiness."""

from __future__ import annotations

from pathlib import Path


def test_application_readiness_docs_exist_and_cover_core_terms() -> None:
    root = Path('docs')
    readiness = root / 'workflows' / 'readiness' / 'APPLICATION_WORKFLOW_READINESS.md'
    guide = root / 'workflows' / 'authoring' / 'WORKFLOW_AUTHOR_GUIDE.md'
    gate = root / 'roadmap' / 'gates' / 'MVP_COMPLETION_GATE.md'

    assert readiness.exists()
    assert guide.exists()
    assert gate.exists()

    assert 'WorkflowContribution' in readiness.read_text()
    assert 'RuntimeAssembler' in readiness.read_text()
    assert 'WorkflowRequirements' in guide.read_text()
    assert 'reference.llm_echo_summary' in guide.read_text()
    assert 'company_agent' in gate.read_text()
    assert 'api.runtime' in gate.read_text()
    assert 'Package Complete' in gate.read_text()
    assert 'application-facing package facade' in gate.read_text()
