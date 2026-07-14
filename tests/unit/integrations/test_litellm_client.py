"""LiteLLM client adapter tests."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from langgraph_automation.integrations.llm.base import LLMResult
from langgraph_automation.integrations.llm.litellm_client import LiteLLMClient


def test_litellm_client_maps_completion_response(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content='hello world'), finish_reason='stop')],
        usage=SimpleNamespace(prompt_tokens=12, completion_tokens=4),
        model='gpt-4o-mini',
    )

    def fake_completion(**kwargs):  # type: ignore[no-untyped-def]
        captured.update(kwargs)
        return response

    monkeypatch.setattr('langgraph_automation.integrations.llm.litellm_client.litellm.completion', fake_completion)

    client = LiteLLMClient(
        model='gpt-4o-mini',
        api_key='api-key-from-settings',
        base_url='https://example.invalid',
        temperature=0.2,
        max_tokens=1024,
    )

    result = client.complete([{'role': 'user', 'content': 'hi'}], top_p=0.9)

    assert isinstance(result, LLMResult)
    assert result.content == 'hello world'
    assert result.raw is response
    assert result.provider == 'litellm'
    assert result.model == 'gpt-4o-mini'
    assert result.input_tokens == 12
    assert result.output_tokens == 4
    assert result.metadata == {'provider': 'litellm', 'model': 'gpt-4o-mini', 'finish_reason': 'stop'}
    assert captured['model'] == 'gpt-4o-mini'
    assert captured['messages'] == [{'role': 'user', 'content': 'hi'}]
    assert captured['api_key'] == 'api-key-from-settings'
    assert captured['base_url'] == 'https://example.invalid'
    assert captured['temperature'] == 0.2
    assert captured['max_tokens'] == 1024
    assert captured['top_p'] == 0.9


def test_litellm_client_propagates_provider_exceptions(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_completion(**kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError('provider failed')

    monkeypatch.setattr('langgraph_automation.integrations.llm.litellm_client.litellm.completion', fake_completion)

    client = LiteLLMClient(model='gpt-4o-mini')

    with pytest.raises(RuntimeError, match='provider failed'):
        client.complete([{'role': 'user', 'content': 'hi'}])
