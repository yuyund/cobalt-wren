"""Docs coverage for the persistence contract test harness."""

from __future__ import annotations

from pathlib import Path


def test_persistence_contract_test_harness_docs_exist_and_cover_core_terms() -> None:
    root = Path('docs')
    harness = root / 'assurance' / 'testing' / 'PERSISTENCE_CONTRACT_TEST_HARNESS.md'
    testing_index = root / 'assurance' / 'testing' / 'index.md'

    assert harness.exists()
    assert testing_index.exists()

    harness_text = harness.read_text().lower()
    index_text = testing_index.read_text().lower()

    for token in (
        'purpose',
        'black-box contract policy',
        'baseline contract',
        'characterization test',
        'test-only backend registry',
        'test-only capability model',
        'durability levels',
        'artifact baseline cases',
        'checkpoint baseline cases',
        'fault injection model',
        'registration guard',
        'runtime wiring regression',
        'runner boundary regression',
        'advanced durable contract catalog',
        'xfail',
        'future backend onboarding procedure',
        'production capability model is not added',
    ):
        assert token in harness_text

    assert 'persistence_contract_test_harness.md' in index_text
