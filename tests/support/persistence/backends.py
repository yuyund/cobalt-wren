"""Test-side persistence backend registry."""

from __future__ import annotations

import importlib
import inspect
import pkgutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from langgraph_automation.integrations.artifact import ArtifactStore, FilesystemArtifactStore, MemoryArtifactStore
from langgraph_automation.integrations.checkpoint import CheckpointStore, MemoryCheckpointStore

from .capabilities import ContractCapability, DurabilityLevel


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
            name='memory',
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
            name='filesystem',
            implementation=FilesystemArtifactStore,
            factory=lambda: FilesystemArtifactStore(Path(tempfile.mkdtemp(prefix='langgraph-automation-artifact-'))),
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
    )


def checkpoint_backend_specs() -> tuple[CheckpointBackendSpec, ...]:
    return (
        CheckpointBackendSpec(
            name='memory',
            implementation=MemoryCheckpointStore,
            factory=MemoryCheckpointStore,
            durability=DurabilityLevel.EPHEMERAL,
            capabilities=frozenset(
                {
                    ContractCapability.BASELINE,
                    ContractCapability.DEFENSIVE_COPY,
                    ContractCapability.RUN_ISOLATION,
                }
            ),
        ),
    )


def _discover_concrete_types(package_name: str, protocol: type) -> frozenset[type]:
    package = importlib.import_module(package_name)
    discovered: set[type] = set()
    ignored_modules = {'base', '__init__', 'keys', 'summary'}
    for module_info in pkgutil.iter_modules(package.__path__, package.__name__ + '.'):
        module_name = module_info.name.rsplit('.', 1)[-1]
        if module_name in ignored_modules:
            continue
        module = importlib.import_module(module_info.name)
        for _, candidate in inspect.getmembers(module, inspect.isclass):
            if candidate.__module__ != module.__name__:
                continue
            if candidate is protocol or getattr(candidate, '_is_protocol', False):
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
    return _discover_concrete_types('langgraph_automation.integrations.artifact', ArtifactStore)


def discover_concrete_checkpoint_store_types() -> frozenset[type[CheckpointStore]]:
    return _discover_concrete_types('langgraph_automation.integrations.checkpoint', CheckpointStore)
