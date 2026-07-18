"""Test-only persistence capability declarations."""

from __future__ import annotations

from enum import StrEnum


class DurabilityLevel(StrEnum):
    """Test-only durability levels."""

    EPHEMERAL = 'ephemeral'
    PROCESS_DURABLE = 'process_durable'
    DEPLOYMENT_DURABLE = 'deployment_durable'


class ContractCapability(StrEnum):
    """Test-only store contract capabilities."""

    BASELINE = 'baseline'
    DEFENSIVE_COPY = 'defensive_copy'
    SAFE_REFERENCE = 'safe_reference'
    RUN_ISOLATION = 'run_isolation'
    IMMUTABLE_WRITE = 'immutable_write'
    IMMUTABLE_VERSION = 'immutable_version'
    IDEMPOTENT_WRITE = 'idempotent_write'
    CONFLICT_DETECTION = 'conflict_detection'
    INTEGRITY_VERIFICATION = 'integrity_verification'
    RESTART_DURABILITY = 'restart_durability'
    SHARED_INSTANCE = 'shared_instance'
    CONCURRENT_WRITE = 'concurrent_write'
    VERSIONED_HISTORY = 'versioned_history'
    SPECIFIC_VERSION_READ = 'specific_version_read'
    LATEST_SELECTION = 'latest_selection'
    HISTORY_LISTING = 'history_listing'
    LINEAGE = 'lineage'
    SERIALIZER_DESCRIPTOR = 'serializer_descriptor'
    THREAD_CONCURRENT_APPEND = 'thread_concurrent_append'
    PROCESS_CONCURRENT_APPEND = 'process_concurrent_append'
