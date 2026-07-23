"""Test-side persistence backend registry."""

from __future__ import annotations

import importlib
import inspect
import pkgutil
import tempfile
from io import BytesIO

import pytest
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from langgraph_automation.integrations.artifact import (
    ArtifactStore,
    FilesystemArtifactStore,
    MemoryArtifactStore,
    S3ArtifactStore,
)
from langgraph_automation.integrations.checkpoint import (
    CheckpointStore,
    FilesystemCheckpointStore,
    MemoryCheckpointStore,
    PostgresCheckpointStore,
)

from .capabilities import ContractCapability, DurabilityLevel


class _FakeS3Client:
    def __init__(self) -> None:
        self.items: dict[str, dict[str, object]] = {}

    def put_object(self, **kwargs: object) -> None:
        key = str(kwargs["Key"])
        if key in self.items:
            raise RuntimeError("412 Precondition")
        self.items[key] = dict(kwargs)

    def get_object(self, **kwargs: object) -> dict[str, object]:
        key = str(kwargs["Key"])
        if key not in self.items:
            raise RuntimeError("404 NoSuchKey")
        item = self.items[key]
        return {"Body": BytesIO(bytes(item["Body"])), "Metadata": item["Metadata"]}

    def list_objects_v2(self, **kwargs: object) -> dict[str, object]:
        prefix = str(kwargs.get("Prefix", ""))
        return {
            "Contents": [{"Key": key} for key in self.items if key.startswith(prefix)],
            "IsTruncated": False,
        }


def _skip_postgres_contract() -> CheckpointStore:
    pytest.skip("PostgreSQL checkpoint contract requires an external test database")


@dataclass(frozen=True, slots=True)
class ArtifactBackendSpec:
    name: str
    implementation: type[ArtifactStore]
    factory: Callable[[], ArtifactStore]
    durability: DurabilityLevel
    capabilities: frozenset[ContractCapability]


@dataclass(frozen=True, slots=True)
class CheckpointBackendSpec:
    name: str
    implementation: type[CheckpointStore]
    factory: Callable[[], CheckpointStore]
    durability: DurabilityLevel
    capabilities: frozenset[ContractCapability]


def artifact_backend_specs() -> tuple[ArtifactBackendSpec, ...]:
    return (
        ArtifactBackendSpec(
            name="memory",
            implementation=MemoryArtifactStore,
            factory=MemoryArtifactStore,
            durability=DurabilityLevel.EPHEMERAL,
            capabilities=frozenset(
                {
                    ContractCapability.BASELINE,
                    ContractCapability.DEFENSIVE_COPY,
                    ContractCapability.SAFE_REFERENCE,
                    ContractCapability.RUN_ISOLATION,
                    ContractCapability.IMMUTABLE_WRITE,
                    ContractCapability.IDEMPOTENT_WRITE,
                    ContractCapability.CONFLICT_DETECTION,
                }
            ),
        ),
        ArtifactBackendSpec(
            name="filesystem",
            implementation=FilesystemArtifactStore,
            factory=lambda: FilesystemArtifactStore(
                Path(tempfile.mkdtemp(prefix="langgraph-automation-artifact-"))
            ),
            durability=DurabilityLevel.PROCESS_DURABLE,
            capabilities=frozenset(
                {
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
                }
            ),
        ),
        ArtifactBackendSpec(
            name="s3",
            implementation=S3ArtifactStore,
            factory=lambda: S3ArtifactStore(bucket="contract", client=_FakeS3Client()),
            durability=DurabilityLevel.DEPLOYMENT_DURABLE,
            capabilities=frozenset(
                {
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
                }
            ),
        ),
    )


def checkpoint_backend_specs() -> tuple[CheckpointBackendSpec, ...]:
    return (
        CheckpointBackendSpec(
            name="memory",
            implementation=MemoryCheckpointStore,
            factory=MemoryCheckpointStore,
            durability=DurabilityLevel.EPHEMERAL,
            capabilities=frozenset(
                {
                    ContractCapability.BASELINE,
                    ContractCapability.DEFENSIVE_COPY,
                    ContractCapability.SAFE_REFERENCE,
                    ContractCapability.RUN_ISOLATION,
                    ContractCapability.IMMUTABLE_VERSION,
                    ContractCapability.IDEMPOTENT_WRITE,
                    ContractCapability.CONFLICT_DETECTION,
                    ContractCapability.SPECIFIC_VERSION_READ,
                    ContractCapability.LATEST_SELECTION,
                    ContractCapability.HISTORY_LISTING,
                    ContractCapability.LINEAGE,
                    ContractCapability.SERIALIZER_DESCRIPTOR,
                    ContractCapability.VERSIONED_HISTORY,
                    ContractCapability.THREAD_CONCURRENT_APPEND,
                    ContractCapability.SHARED_INSTANCE,
                }
            ),
        ),
        CheckpointBackendSpec(
            name="filesystem",
            implementation=FilesystemCheckpointStore,
            factory=lambda: FilesystemCheckpointStore(
                Path(tempfile.mkdtemp(prefix="langgraph-automation-checkpoint-"))
            ),
            durability=DurabilityLevel.PROCESS_DURABLE,
            capabilities=frozenset(
                {
                    ContractCapability.BASELINE,
                    ContractCapability.DEFENSIVE_COPY,
                    ContractCapability.SAFE_REFERENCE,
                    ContractCapability.RUN_ISOLATION,
                    ContractCapability.IMMUTABLE_VERSION,
                    ContractCapability.IDEMPOTENT_WRITE,
                    ContractCapability.CONFLICT_DETECTION,
                    ContractCapability.INTEGRITY_VERIFICATION,
                    ContractCapability.RESTART_DURABILITY,
                    ContractCapability.SPECIFIC_VERSION_READ,
                    ContractCapability.LATEST_SELECTION,
                    ContractCapability.HISTORY_LISTING,
                    ContractCapability.LINEAGE,
                    ContractCapability.SERIALIZER_DESCRIPTOR,
                    ContractCapability.VERSIONED_HISTORY,
                    ContractCapability.SHARED_INSTANCE,
                    ContractCapability.THREAD_CONCURRENT_APPEND,
                    ContractCapability.PROCESS_CONCURRENT_APPEND,
                }
            ),
        ),
        CheckpointBackendSpec(
            name="postgres",
            implementation=PostgresCheckpointStore,
            factory=_skip_postgres_contract,
            durability=DurabilityLevel.DEPLOYMENT_DURABLE,
            capabilities=frozenset(
                {
                    ContractCapability.BASELINE,
                    ContractCapability.DEFENSIVE_COPY,
                    ContractCapability.SAFE_REFERENCE,
                    ContractCapability.RUN_ISOLATION,
                    ContractCapability.IMMUTABLE_VERSION,
                    ContractCapability.IDEMPOTENT_WRITE,
                    ContractCapability.CONFLICT_DETECTION,
                    ContractCapability.INTEGRITY_VERIFICATION,
                    ContractCapability.RESTART_DURABILITY,
                    ContractCapability.SPECIFIC_VERSION_READ,
                    ContractCapability.LATEST_SELECTION,
                    ContractCapability.HISTORY_LISTING,
                    ContractCapability.LINEAGE,
                    ContractCapability.SERIALIZER_DESCRIPTOR,
                    ContractCapability.VERSIONED_HISTORY,
                    ContractCapability.SHARED_INSTANCE,
                    ContractCapability.PROCESS_CONCURRENT_APPEND,
                }
            ),
        ),
    )


def _discover_concrete_types(package_name: str, protocol: type) -> frozenset[type]:
    package = importlib.import_module(package_name)
    discovered: set[type] = set()
    ignored_modules = {"base", "__init__", "keys", "summary"}
    for module_info in pkgutil.iter_modules(package.__path__, package.__name__ + "."):
        module_name = module_info.name.rsplit(".", 1)[-1]
        if module_name in ignored_modules:
            continue
        module = importlib.import_module(module_info.name)
        for _, candidate in inspect.getmembers(module, inspect.isclass):
            if candidate.__module__ != module.__name__:
                continue
            if candidate is protocol or getattr(candidate, "_is_protocol", False):
                continue
            if inspect.isabstract(candidate):
                continue
            try:
                if issubclass(candidate, protocol):
                    discovered.add(candidate)
            except TypeError:
                continue
    return frozenset(discovered)


def discover_concrete_artifact_store_types() -> frozenset[type[ArtifactStore]]:
    return _discover_concrete_types(
        "langgraph_automation.integrations.artifact", ArtifactStore
    )


def discover_concrete_checkpoint_store_types() -> frozenset[type[CheckpointStore]]:
    return _discover_concrete_types(
        "langgraph_automation.integrations.checkpoint", CheckpointStore
    )
