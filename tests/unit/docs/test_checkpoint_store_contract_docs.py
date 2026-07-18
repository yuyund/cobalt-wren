"""Docs coverage for the checkpoint store contract."""

from __future__ import annotations

from pathlib import Path


def test_checkpoint_store_contract_docs_exist_and_cover_core_terms() -> None:
    contract = Path('docs') / 'contracts' / 'integrations' / 'CHECKPOINT_STORE.md'
    api_surface = Path('docs') / 'api' / 'surface' / 'API_SURFACE.md'
    core_contract = Path('docs') / 'contracts' / 'core' / 'CONTRACTS.md'

    for path in (contract, api_surface, core_contract):
        assert path.exists()

    contract_text = contract.read_text().lower()
    api_surface_text = api_surface.read_text().lower()
    core_contract_text = core_contract.read_text().lower()

    for token in (
        'checkpoint store contract',
        'approved_for_implementation',
        'execution stream identity',
        'complete checkpoint identity',
        'checkpointwriterequest',
        'storedcheckpoint',
        'checkpointreadresult',
        'append-only',
        'linear history',
        'caller-issued',
        'store-assigned revision',
        'load_latest',
        'load_checkpoint',
        'list_for_run',
        'no delete',
        'memorycheckpointstore',
        'ephemeral',
    ):
        assert token in contract_text

    for token in (
        'checkpointwriterequest',
        'storedcheckpoint',
        'checkpointreadresult',
        'checkpointstore',
        'approved for durable backend implementation',
    ):
        assert token in api_surface_text

    for token in (
        'checkpointstore contract',
        'checkpointwriterequest',
        'storedcheckpoint',
        'checkpointreadresult',
        'approved_for_implementation',
    ):
        assert token in core_contract_text
