"""Test doubles for observability context rebinding."""

from __future__ import annotations

from dataclasses import dataclass

from langgraph_automation.integrations.observability.types import ObservabilityContext


@dataclass(slots=True)
class ObservabilityBoundDouble:
    label: str
    bound_context: ObservabilityContext | None = None

    def with_observability_context(self, context: ObservabilityContext) -> 'ObservabilityBoundDouble':
        return ObservabilityBoundDouble(label=self.label, bound_context=context)
