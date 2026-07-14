"""Concrete LiteLLM-backed LLM adapter."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import litellm

from langgraph_automation.integrations.llm.base import LLMResult


class LiteLLMClient:
    """Concrete adapter that invokes litellm.completion."""

    provider = 'litellm'

    def __init__(
        self,
        *,
        model: str,
        api_key: str | None = None,
        base_url: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> None:
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.temperature = temperature
        self.max_tokens = max_tokens

    def _completion_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = {'model': self.model}
        if self.api_key:
            kwargs['api_key'] = self.api_key
        if self.base_url:
            kwargs['base_url'] = self.base_url
        if self.temperature is not None:
            kwargs['temperature'] = self.temperature
        if self.max_tokens is not None:
            kwargs['max_tokens'] = self.max_tokens
        return kwargs

    @staticmethod
    def _get_value(payload: Any, name: str, default: Any = None) -> Any:
        if isinstance(payload, Mapping):
            return payload.get(name, default)
        return getattr(payload, name, default)

    def complete(self, messages: list[dict[str, Any]], **kwargs: Any) -> LLMResult:
        completion_kwargs = self._completion_kwargs()
        completion_kwargs['messages'] = messages
        completion_kwargs.update(kwargs)
        response = litellm.completion(**completion_kwargs)

        choice = None
        choices = self._get_value(response, 'choices', [])
        if choices:
            choice = choices[0]
        message = self._get_value(choice, 'message', None) if choice is not None else None
        content = self._get_value(message, 'content', '') if message is not None else ''
        finish_reason = self._get_value(choice, 'finish_reason', '') if choice is not None else ''

        usage = self._get_value(response, 'usage', None)
        input_tokens = self._get_value(usage, 'prompt_tokens', None) if usage is not None else None
        output_tokens = self._get_value(usage, 'completion_tokens', None) if usage is not None else None
        response_model = self._get_value(response, 'model', self.model) or self.model
        metadata = {
            'provider': self.provider,
            'model': response_model,
        }
        if finish_reason:
            metadata['finish_reason'] = finish_reason

        return LLMResult(
            content='' if content is None else str(content),
            raw=response,
            provider=self.provider,
            model=str(response_model),
            input_tokens=None if input_tokens is None else int(input_tokens),
            output_tokens=None if output_tokens is None else int(output_tokens),
            metadata=metadata,
        )
