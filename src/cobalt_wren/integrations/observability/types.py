'''Lightweight observability payload types.'''

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any


@dataclass(slots=True, frozen=True)
class SpanRef:
    '''Opaque span reference passed through the execution plane.'''

    span_id: str


@dataclass(slots=True, frozen=True)
class EventPayload:
    '''Normalized event payload used by sinks and runners.'''

    message: str = ''
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class SpanPayload:
    '''Normalized span payload used by sinks and runners.'''

    name: str
    node_name: str = ''
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class ObservabilityContext:
    '''Execution context carried through runtime and observed wrappers.'''

    run_id: int | None = None
    thread_id: str = ''
    parent_span: SpanRef | None = None
    node_name: str = ''

    def with_parent_span(self, parent_span: SpanRef | None, node_name: str | None = None) -> 'ObservabilityContext':
        return replace(self, parent_span=parent_span, node_name=self.node_name if node_name is None else node_name)
