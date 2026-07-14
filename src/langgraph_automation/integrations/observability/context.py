"""Observability context binding helpers for optional observed dependencies."""

from __future__ import annotations

from typing import Protocol, Self, TypeVar, runtime_checkable

from .types import ObservabilityContext


@runtime_checkable
class SupportsObservabilityContext(Protocol):
    """Protocol for dependencies that can be rebound to a new observability context."""

    def with_observability_context(self, context: ObservabilityContext) -> Self: ...


T = TypeVar('T')


def bind_observability_context(obj: T | None, context: ObservabilityContext) -> T | None:
    """Rebind dependencies that support observability context propagation."""

    if obj is None:
        return None
    method = getattr(obj, 'with_observability_context', None)
    if callable(method):
        return method(context)
    return obj
