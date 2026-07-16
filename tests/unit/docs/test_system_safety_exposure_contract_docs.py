"""Docs coverage for the system safety exposure contract."""

from __future__ import annotations

from pathlib import Path


def test_system_safety_exposure_contract_docs_exist_and_cover_core_terms() -> None:
    root = Path('docs')
    contract = root / 'assurance' / 'contracts' / 'SYSTEM_SAFETY_EXPOSURE_CONTRACT.md'

    assert contract.exists()

    text = contract.read_text()
    for token in (
        'unsafe data taxonomy',
        'safe data taxonomy',
        'persistence safety contract',
        'admin display safety contract',
        'dynamic ui display safety contract',
        'observability metadata safety contract',
        'error message safety contract',
        'artifact/checkpoint body-vs-metadata separation',
        'deferred work',
        'durable artifact/checkpoint backend is deferred',
        'api.runtime is deferred',
        'run_workflow is deferred',
        'application workflow is deferred',
        'company_agent is deferred',
    ):
        assert token in text.lower()
