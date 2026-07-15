"""Docs coverage for package facade design."""

from __future__ import annotations

from pathlib import Path


def test_package_facade_design_docs_exist_and_cover_core_terms() -> None:
    root = Path('docs')
    design = root / 'PACKAGE_FACADE_DESIGN.md'
    adr = root / 'adr' / '0013-package-facade-design.md'

    assert design.exists()
    assert adr.exists()

    design_text = design.read_text()
    adr_text = adr.read_text()

    for token in (
        'langgraph_automation.api.engine',
        'create_engine',
        'AutomationEngine',
        'EnginePreparedWorkflow',
        'run_workflow',
        'api.runtime',
        'PluginRegistry',
        'WorkflowPreparer',
        'RuntimeAssembler',
        'ConfigValidator',
        'Block M',
        'Block O',
        'implemented',
        'block o routes the service bridge through `api.engine`',
    ):
        assert token.lower() in design_text.lower() or token.lower() in adr_text.lower()

    assert 'public-facing provisional' in design_text
    assert 'preparation only' in adr_text.lower()
    assert 'verification' in design_text.lower()
    assert 'application-facing package facade' in design_text.lower() or 'package-facing facade' in design_text.lower()
    assert 'temporary exception has been removed' in design_text.lower()
