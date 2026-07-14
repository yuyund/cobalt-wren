"""Graph registry mechanism and dependency metadata.

This module provides the foundation-side registry abstraction only. Concrete
workflow definitions are composed elsewhere and injected into a registry
instance by the service layer.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

from langgraph_automation.graphs.constants import DEFAULT_GRAPH_KIND
from langgraph_automation.graphs.types import GraphDefinition, GraphRuntimeRequirements


class UnknownGraphKindError(ValueError):
    """Raised when a workflow requests an unsupported graph kind."""


@dataclass(frozen=True, slots=True)
class GraphRegistry:
    """In-memory registry for graph definitions."""

    definitions: tuple[GraphDefinition, ...] = ()
    _definitions_by_kind: dict[str, GraphDefinition] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        by_kind: dict[str, GraphDefinition] = {}
        for definition in self.definitions:
            if definition.kind in by_kind:
                raise ValueError(f'duplicate graph kind: {definition.kind}')
            by_kind[definition.kind] = definition
        object.__setattr__(self, '_definitions_by_kind', by_kind)

    @property
    def definitions_by_kind(self) -> Mapping[str, GraphDefinition]:
        return self._definitions_by_kind

    def get(self, kind: str) -> GraphDefinition:
        try:
            return self._definitions_by_kind[kind]
        except KeyError as exc:
            raise UnknownGraphKindError(f'Unsupported graph kind: {kind}') from exc

    def supported_graph_kinds(self) -> tuple[str, ...]:
        return tuple(self._definitions_by_kind.keys())

    def graph_requirements(self) -> dict[str, GraphRuntimeRequirements]:
        return {kind: definition.requirements for kind, definition in self._definitions_by_kind.items()}


def build_graph_registry(definitions: Iterable[GraphDefinition]) -> GraphRegistry:
    return GraphRegistry(tuple(definitions))


def default_graph_kind() -> str:
    return DEFAULT_GRAPH_KIND


def get_graph_definition(kind: str, registry: GraphRegistry) -> GraphDefinition:
    return registry.get(kind)


def supported_graph_kinds(registry: GraphRegistry) -> tuple[str, ...]:
    return registry.supported_graph_kinds()


def graph_requirements(registry: GraphRegistry) -> dict[str, GraphRuntimeRequirements]:
    return registry.graph_requirements()
