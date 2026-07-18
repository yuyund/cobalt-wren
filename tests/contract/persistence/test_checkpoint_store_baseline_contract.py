"""Reusable baseline contract tests for versioned CheckpointStore implementations."""

from __future__ import annotations

import pytest

from tests.support.persistence import (
    assert_checkpoint_concurrent_append,
    assert_checkpoint_defensive_copy,
    assert_checkpoint_descriptor_derivation,
    assert_checkpoint_diagnostic_non_exposure,
    assert_checkpoint_integrity_error_is_representable,
    assert_checkpoint_idempotency_and_conflict,
    assert_checkpoint_missing_behavior,
    assert_checkpoint_namespace_isolation,
    assert_checkpoint_run_isolation,
    assert_checkpoint_validation_contract,
    assert_checkpoint_versioned_round_trip,
    checkpoint_backend_specs,
)


@pytest.mark.parametrize('backend_spec', checkpoint_backend_specs(), ids=lambda spec: spec.name)
def test_checkpoint_store_baseline_contract_suite(backend_spec) -> None:
    store = backend_spec.factory()

    assert_checkpoint_versioned_round_trip(store)
    assert_checkpoint_missing_behavior(store)
    assert_checkpoint_run_isolation(store)
    assert_checkpoint_namespace_isolation(store)
    assert_checkpoint_defensive_copy(store)
    assert_checkpoint_idempotency_and_conflict(store)
    assert_checkpoint_descriptor_derivation(store)
    assert_checkpoint_diagnostic_non_exposure(store)
    assert_checkpoint_validation_contract()
    assert_checkpoint_integrity_error_is_representable()
    assert_checkpoint_concurrent_append(backend_spec.factory)
