"""Persistence contract test support."""

from .backends import (
    ArtifactBackendSpec,
    CheckpointBackendSpec,
    artifact_backend_specs,
    checkpoint_backend_specs,
    discover_concrete_artifact_store_types,
    discover_concrete_checkpoint_store_types,
)
from .capabilities import ContractCapability, DurabilityLevel
from .contracts import (
    assert_artifact_defensive_copy,
    assert_artifact_diagnostic_non_exposure,
    assert_artifact_missing_behavior,
    assert_artifact_run_isolation,
    assert_artifact_round_trip,
    assert_artifact_safe_reference_rejected,
    assert_checkpoint_defensive_copy,
    assert_checkpoint_delete_contract,
    assert_checkpoint_diagnostic_non_exposure,
    assert_checkpoint_latest_state_compatibility,
    assert_checkpoint_missing_behavior,
    assert_checkpoint_run_isolation,
    assert_checkpoint_round_trip,
)
from .faults import (
    FaultPlan,
    FaultRecord,
    FaultTiming,
    FaultingArtifactStore,
    FaultingCheckpointStore,
)

__all__ = [
    'ArtifactBackendSpec',
    'CheckpointBackendSpec',
    'ContractCapability',
    'DurabilityLevel',
    'FaultPlan',
    'FaultRecord',
    'FaultTiming',
    'FaultingArtifactStore',
    'FaultingCheckpointStore',
    'assert_artifact_defensive_copy',
    'assert_artifact_diagnostic_non_exposure',
    'assert_artifact_missing_behavior',
    'assert_artifact_run_isolation',
    'assert_artifact_round_trip',
    'assert_artifact_safe_reference_rejected',
    'assert_checkpoint_defensive_copy',
    'assert_checkpoint_delete_contract',
    'assert_checkpoint_diagnostic_non_exposure',
    'assert_checkpoint_latest_state_compatibility',
    'assert_checkpoint_missing_behavior',
    'assert_checkpoint_run_isolation',
    'assert_checkpoint_round_trip',
    'artifact_backend_specs',
    'checkpoint_backend_specs',
    'discover_concrete_artifact_store_types',
    'discover_concrete_checkpoint_store_types',
]
