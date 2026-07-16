"""Reusable baseline contract tests for ArtifactStore implementations."""

from __future__ import annotations

import pytest

from tests.support.persistence import (
    artifact_backend_specs,
    assert_artifact_digest_and_size,
    assert_artifact_defensive_copy,
    assert_artifact_diagnostic_non_exposure,
    assert_artifact_idempotency_and_conflict,
    assert_artifact_integrity_errors_are_representable,
    assert_artifact_list_order_is_deterministic,
    assert_artifact_missing_behavior,
    assert_artifact_run_isolation,
    assert_artifact_round_trip,
    assert_artifact_read_result_repr_safety,
    assert_artifact_safe_storage_key_validation,
    assert_artifact_safe_reference_rejected,
    assert_artifact_storage_value_copy,
)


@pytest.mark.parametrize('backend_spec', artifact_backend_specs(), ids=lambda spec: spec.name)
def test_artifact_store_baseline_contract_suite(backend_spec) -> None:
    store = backend_spec.factory()

    assert_artifact_round_trip(store)
    assert_artifact_missing_behavior(store)
    assert_artifact_run_isolation(store)
    assert_artifact_defensive_copy(store)
    assert_artifact_safe_reference_rejected(store)
    assert_artifact_diagnostic_non_exposure(store)
    assert_artifact_idempotency_and_conflict(store)
    assert_artifact_storage_value_copy(store)
    assert_artifact_digest_and_size(store)
    assert_artifact_list_order_is_deterministic(store)
    assert_artifact_safe_storage_key_validation(store)
    assert_artifact_read_result_repr_safety(store)
    assert_artifact_integrity_errors_are_representable()
