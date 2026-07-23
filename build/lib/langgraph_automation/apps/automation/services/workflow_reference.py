"""Control-plane workflow reference parsing."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from langgraph_automation.apps.automation.services.errors import WorkflowConfigurationError


@dataclass(frozen=True, slots=True)
class WorkflowReference:
    kind: str
    config: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "config", dict(self.config))


def parse_workflow_reference(definition_payload: object) -> WorkflowReference | None:
    """Return a public workflow reference, or None for the legacy graph path."""
    if not isinstance(definition_payload, Mapping):
        return None
    raw = definition_payload.get("workflow")
    if raw is None:
        return None
    if not isinstance(raw, Mapping):
        raise WorkflowConfigurationError("workflow must be a mapping.")
    kind = raw.get("kind")
    if not isinstance(kind, str) or not kind.strip():
        raise WorkflowConfigurationError("workflow.kind must be a non-empty string.")
    config = raw.get("config", {})
    if not isinstance(config, Mapping):
        raise WorkflowConfigurationError("workflow.config must be a mapping.")
    return WorkflowReference(kind=kind.strip(), config=dict(config))
