"""Framework-neutral execution result used by the Django control plane."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ControlPlaneExecutionResult:
    status: str
    output_payload: Mapping[str, object] = field(default_factory=dict)
    error_message: str = ""
    last_step_name: str = ""
    message: str = ""
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "output_payload", dict(self.output_payload))
        object.__setattr__(self, "details", dict(self.details))
