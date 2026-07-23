"""Factory context passed to runtime contribution hooks."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from langgraph_automation.config.models import LimitsConfig, SafetyConfig

from .secrets import SecretResolver

__all__ = ["FactoryContext"]


@dataclass(frozen=True, slots=True)
class FactoryContext:
    environment: str
    secrets: SecretResolver
    limits: LimitsConfig
    observability: Mapping[str, object] = field(default_factory=dict)
    safety: SafetyConfig = field(default_factory=SafetyConfig)

    def __post_init__(self) -> None:
        object.__setattr__(self, "observability", dict(self.observability))
