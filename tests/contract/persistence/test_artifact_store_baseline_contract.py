"""Reusable baseline contract tests for ArtifactStore implementations."""

from __future__ import annotations

import pytest

from tests.support.persistence import (
    artifact_backend_specs,
    assert_artifact_defensive_copy,
    assert_artifact_diagnostic_non_exposure,
    assert_artifact_missing_behavior,
    assert_artifact_run_isolation,
    assert_artifact_round_trip,
    assert_artifact_safe_reference_rejected,
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

