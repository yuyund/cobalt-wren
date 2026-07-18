"""Concrete runtime dependencies assembled from validated package config."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from langgraph_automation.integrations.checkpoint.base import CheckpointStore

__all__ = ["RuntimeDependencies"]


def _copy_mapping(mapping: Mapping[str, Any] | None) -> dict[str, Any]:
    return dict(mapping or {})


@dataclass(frozen=True, slots=True)
class RuntimeDependencies:
    providers: Mapping[str, object]
    tools: Mapping[str, object]
    artifact_store: object | None = None
    checkpoint_store: CheckpointStore | None = None
    event_sinks: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "providers", _copy_mapping(self.providers))
        object.__setattr__(self, "tools", _copy_mapping(self.tools))
        object.__setattr__(self, "event_sinks", _copy_mapping(self.event_sinks))
