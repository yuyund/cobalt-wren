"""Observability decorator for LLM clients."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

from langgraph_automation.core.redaction import redact_text
from langgraph_automation.core.summary import preview_text, summarize_messages
from langgraph_automation.integrations.llm.base import LLMClient, LLMResult
from langgraph_automation.integrations.observability.base import EventSink
from langgraph_automation.integrations.observability.events import SPAN_LLM
from langgraph_automation.integrations.observability.failure_policy import suppress_observability_failure
from langgraph_automation.integrations.observability.types import ObservabilityContext


def _provider_name(result: LLMResult, inner: LLMClient) -> str:
    provider = result.provider or getattr(inner, 'provider', '')
    return provider or 'unknown'


def _model_name(result: LLMResult, inner: LLMClient) -> str:
    model = result.model or getattr(inner, 'model', '')
    return model or 'unknown'


def _metrics_from_result(result: LLMResult) -> dict[str, int]:
    metrics: dict[str, int] = {}
    if result.input_tokens is not None:
        metrics['input_tokens'] = int(result.input_tokens)
    if result.output_tokens is not None:
        metrics['output_tokens'] = int(result.output_tokens)
    if result.input_tokens is not None or result.output_tokens is not None:
        metrics['total_tokens'] = int((result.input_tokens or 0) + (result.output_tokens or 0))
    return metrics


def _output_summary(result: LLMResult) -> str:
    payload = {
        'length': len(result.content),
        'preview': preview_text(redact_text(result.content)),
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)


@dataclass(slots=True)
class ObservedLLMClient:
    """Decorator that records LLM calls as observability spans."""

    inner: LLMClient
    event_sink: EventSink | None
    observability: ObservabilityContext

    def complete(self, messages: list[dict[str, Any]], **kwargs: Any) -> LLMResult:
        input_summary = summarize_messages(messages)
        start_metadata = {
            'provider': getattr(self.inner, 'provider', '') or 'unknown',
            'model': getattr(self.inner, 'model', '') or 'unknown',
            'input_summary': input_summary,
        }

        if self.event_sink is None:
            return self.inner.complete(messages, **kwargs)

        span = self.event_sink.span_started(
            self.observability.run_id or 0,
            span_type=SPAN_LLM,
            name=f"llm:{start_metadata['model']}",
            node_name=self.observability.node_name,
            parent=self.observability.parent_span,
            metadata=start_metadata,
        )

        try:
            result = self.inner.complete(messages, **kwargs)
        except Exception as primary_exc:
            error_message = redact_text(str(primary_exc))
            suppress_observability_failure(
                lambda: self.event_sink.span_failed(
                    span,
                    error_message=error_message,
                    metadata={
                        'provider': start_metadata['provider'],
                        'model': start_metadata['model'],
                    },
                ),
                context={
                    'component': 'ObservedLLMClient',
                    'operation': 'span_failed',
                },
            )
            raise

        self.event_sink.span_completed(
            span,
            output_summary=_output_summary(result),
            metrics=_metrics_from_result(result),
            metadata={
                'provider': _provider_name(result, self.inner),
                'model': _model_name(result, self.inner),
            },
        )
        return result

    def with_observability_context(self, context: ObservabilityContext) -> 'ObservedLLMClient':
        return ObservedLLMClient(inner=self.inner, event_sink=self.event_sink, observability=context)
