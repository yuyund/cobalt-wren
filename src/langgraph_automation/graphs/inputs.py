"""Transient execution input helpers for graph nodes.

This boundary keeps raw Run.input_payload out of checkpointable graph state.
Nodes may read only the minimal text they need through GraphRuntime.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class GraphExecutionInput:
    """Minimal transient input made available to nodes during execution."""

    text: str = ''
    prompt: str = ''

    @property
    def primary_text(self) -> str:
        """Return the first available user text field."""

        return self.text or self.prompt

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any] | None) -> 'GraphExecutionInput':
        """Extract safe transient input fields from a raw payload mapping."""

        if not isinstance(payload, Mapping):
            return cls()

        text_value = payload.get('text')
        prompt_value = payload.get('prompt')
        text = text_value.strip() if isinstance(text_value, str) else ''
        prompt = prompt_value.strip() if isinstance(prompt_value, str) else ''
        return cls(text=text, prompt=prompt)
