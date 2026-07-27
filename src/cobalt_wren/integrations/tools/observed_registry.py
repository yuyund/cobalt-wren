"""Observability decorator for tool registries."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

from cobalt_wren.core.redaction import redact_text
from cobalt_wren.core.summary import preview_text, summarize_mapping, summarize_value
from cobalt_wren.integrations.observability.base import EventSink
from cobalt_wren.integrations.observability.events import SPAN_TOOL
from cobalt_wren.integrations.observability.failure_policy import suppress_observability_failure
from cobalt_wren.integrations.observability.types import ObservabilityContext
from cobalt_wren.integrations.tools.base import ToolRegistry, ToolResult


def _input_summary(name: str, kwargs: dict[str, Any]) -> dict[str, Any]:
    return {
        'tool_name': name,
        'arg_keys': sorted(kwargs.keys()),
        'kwargs_preview': summarize_mapping(kwargs),
    }


def _output_summary(result: ToolResult) -> str:
    if result.output_summary:
        preview_source = result.output_summary
    elif isinstance(result.output, str):
        preview_source = result.output
    else:
        preview_source = json.dumps(summarize_value(result.output), ensure_ascii=False, sort_keys=True, default=str)
    payload = {
        'exit_code': result.exit_code,
        'length': len(preview_source),
        'preview': preview_text(preview_source),
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)


def _tool_result_metadata(name: str, result: ToolResult) -> dict[str, Any]:
    merged = {
        'tool_name': name,
        'tool_result_metadata': result.metadata,
    }
    return summarize_mapping(merged)


def _failure_message(result: ToolResult) -> str:
    if result.error_message:
        return redact_text(result.error_message)
    return f'tool {result.exit_code} failed'


@dataclass(slots=True)
class ObservedToolRegistry:
    """Decorator that records tool calls as observability spans."""

    inner: ToolRegistry
    event_sink: EventSink | None
    observability: ObservabilityContext

    def run(self, name: str, **kwargs: Any) -> ToolResult:
        input_summary = _input_summary(name, kwargs)

        event_sink = self.event_sink
        if event_sink is None:
            return self.inner.run(name, **kwargs)

        span = event_sink.span_started(
            self.observability.run_id or 0,
            span_type=SPAN_TOOL,
            name=f'tool:{name}',
            node_name=self.observability.node_name,
            parent=self.observability.parent_span,
            metadata={
                'tool_name': name,
                'input_summary': input_summary,
            },
        )

        try:
            result = self.inner.run(name, **kwargs)
        except Exception as primary_exc:
            error_message = redact_text(str(primary_exc))
            suppress_observability_failure(
                lambda: event_sink.span_failed(
                    span,
                    error_message=error_message,
                    metadata={
                        'tool_name': name,
                        'input_summary': input_summary,
                    },
                ),
                context={
                    'component': 'ObservedToolRegistry',
                    'operation': 'span_failed',
                    'tool_name': name,
                },
            )
            raise

        result_metadata = _tool_result_metadata(name, result)
        metrics = {'exit_code': result.exit_code}
        if result.exit_code != 0 or bool(result.error_message):
            failure_message = _failure_message(result)
            suppress_observability_failure(
                lambda: event_sink.span_failed(
                    span,
                    error_message=failure_message,
                    metrics=metrics,
                    metadata={
                        'tool_name': name,
                        'input_summary': input_summary,
                        'result_metadata': result_metadata,
                    },
                ),
                context={
                    'component': 'ObservedToolRegistry',
                    'operation': 'span_failed',
                    'tool_name': name,
                },
            )
            return result

        event_sink.span_completed(
            span,
            output_summary=_output_summary(result),
            metrics=metrics,
            metadata={
                'tool_name': name,
                'input_summary': input_summary,
                'result_metadata': result_metadata,
            },
        )
        return result

    def with_observability_context(self, context: ObservabilityContext) -> 'ObservedToolRegistry':
        return ObservedToolRegistry(inner=self.inner, event_sink=self.event_sink, observability=context)
