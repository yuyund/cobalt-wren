"""LLM integration interfaces and normalized response types."""

from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Mapping, Sequence
from typing import Any, Protocol, TypeAlias, runtime_checkable


LLMRequest: TypeAlias = Sequence[Mapping[str, Any]]


@dataclass(slots=True, frozen=True)
class LLMResult:
    """Normalized response returned by all LLM adapters."""

    content: str = ''
    raw: Any = None
    provider: str = ''
    model: str = ''
    input_tokens: int | None = None
    output_tokens: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class LLMClient(Protocol):
    def complete(self, messages: LLMRequest, **kwargs: Any) -> LLMResult: ...
