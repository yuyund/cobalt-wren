"""Test doubles for LLM client wrappers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from cobalt_wren.integrations.llm.base import LLMResult


@dataclass(slots=True)
class RecordedLLMCall:
    messages: list[dict[str, Any]]
    kwargs: dict[str, Any] = field(default_factory=dict)


class RecordingLLMClient:
    def __init__(self, result: LLMResult | None = None) -> None:
        self.result = result or LLMResult(content='ok', provider='fake', model='test-model', input_tokens=3, output_tokens=2, raw={'provider_response': 'hidden'})
        self.provider = self.result.provider
        self.model = self.result.model
        self.calls: list[RecordedLLMCall] = []

    def complete(self, messages: list[dict[str, Any]], **kwargs: Any) -> LLMResult:
        self.calls.append(RecordedLLMCall(messages=[dict(message) for message in messages], kwargs=dict(kwargs)))
        return self.result


class FailingLLMClient:
    def __init__(self, exc: Exception | None = None, provider: str = '', model: str = '') -> None:
        self.exc = exc or RuntimeError('llm failure')
        self.provider = provider
        self.model = model
        self.calls: list[RecordedLLMCall] = []

    def complete(self, messages: list[dict[str, Any]], **kwargs: Any) -> LLMResult:
        self.calls.append(RecordedLLMCall(messages=[dict(message) for message in messages], kwargs=dict(kwargs)))
        raise self.exc
