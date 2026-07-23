"""Registration guard for concrete persistence backends."""

from __future__ import annotations

from tests.support.persistence import (
    ContractCapability,
    DurabilityLevel,
    artifact_backend_specs,
    checkpoint_backend_specs,
    discover_concrete_artifact_store_types,
    discover_concrete_checkpoint_store_types,
)


def test_artifact_backend_registry_covers_all_concrete_implementations() -> None:
    specs = artifact_backend_specs()
    registered = {spec.implementation for spec in specs}
    discovered = discover_concrete_artifact_store_types()

    assert discovered == registered
    assert {spec.name for spec in specs} == {"memory", "filesystem", "s3"}
    assert {spec.durability for spec in specs} == {
        DurabilityLevel.EPHEMERAL,
        DurabilityLevel.PROCESS_DURABLE,
        DurabilityLevel.DEPLOYMENT_DURABLE,
    }
    assert {
        ContractCapability.BASELINE,
        ContractCapability.DEFENSIVE_COPY,
        ContractCapability.SAFE_REFERENCE,
        ContractCapability.RUN_ISOLATION,
        ContractCapability.IMMUTABLE_WRITE,
        ContractCapability.IDEMPOTENT_WRITE,
        ContractCapability.CONFLICT_DETECTION,
        ContractCapability.INTEGRITY_VERIFICATION,
        ContractCapability.RESTART_DURABILITY,
        ContractCapability.SHARED_INSTANCE,
        ContractCapability.CONCURRENT_WRITE,
    } <= set().union(*(spec.capabilities for spec in specs))


def test_checkpoint_backend_registry_covers_all_concrete_implementations() -> None:
    specs = checkpoint_backend_specs()
    registered = {spec.implementation for spec in specs}
    discovered = discover_concrete_checkpoint_store_types()

    assert discovered == registered
    assert {spec.name for spec in specs} == {"memory", "filesystem", "postgres"}
    assert {spec.durability for spec in specs} == {
        DurabilityLevel.EPHEMERAL,
        DurabilityLevel.PROCESS_DURABLE,
        DurabilityLevel.DEPLOYMENT_DURABLE,
    }
    assert {
        ContractCapability.BASELINE,
        ContractCapability.DEFENSIVE_COPY,
        ContractCapability.RUN_ISOLATION,
        ContractCapability.IMMUTABLE_VERSION,
        ContractCapability.IDEMPOTENT_WRITE,
        ContractCapability.CONFLICT_DETECTION,
        ContractCapability.SPECIFIC_VERSION_READ,
        ContractCapability.LATEST_SELECTION,
        ContractCapability.HISTORY_LISTING,
        ContractCapability.LINEAGE,
        ContractCapability.SERIALIZER_DESCRIPTOR,
    } <= set().union(*(spec.capabilities for spec in specs))
