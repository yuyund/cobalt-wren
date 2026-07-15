"""Docs coverage for package completion and verification strategy."""

from __future__ import annotations

from pathlib import Path


def test_package_completion_docs_exist_and_cover_core_terms() -> None:
    root = Path('docs')
    completion = root / 'PACKAGE_COMPLETION.md'
    verification = root / 'PACKAGE_VERIFICATION_STRATEGY.md'

    assert completion.exists()
    assert verification.exists()

    completion_text = completion.read_text()
    verification_text = verification.read_text()

    assert 'application-facing package facade' in completion_text
    assert 'langgraph_automation.api.engine' in completion_text
    assert 'PluginRegistry' in completion_text
    assert 'WorkflowPreparer' in completion_text
    assert 'company_agent' in completion_text

    for token in ('L0', 'L1', 'L2', 'L3', 'L4', 'L5', 'L6'):
        assert token in verification_text
    assert 'failure matrix' in verification_text.lower()
    assert 'transitional bridge' in verification_text.lower()
