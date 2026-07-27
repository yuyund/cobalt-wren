"""Public LLM API facade."""

from __future__ import annotations

from cobalt_wren.integrations.llm.base import LLMClient, LLMRequest, LLMResult

__all__ = [
    'LLMClient',
    'LLMRequest',
    'LLMResult',
]
