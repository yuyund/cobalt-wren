'''Django-backed observability sink.'''

from __future__ import annotations

from collections.abc import Mapping, Sequence
import json
from typing import Any

from django.db import transaction
from django.utils import timezone

from langgraph_automation.apps.automation.models.artifact import Artifact
from langgraph_automation.apps.automation.models.checkpoint import CheckpointMetadata
from langgraph_automation.apps.automation.models.event import RunEvent, RunEventLevel
from langgraph_automation.apps.automation.models.execution import ExecutionSpan, ExecutionSpanStatus
from langgraph_automation.apps.automation.models.run import Run
from langgraph_automation.core.redaction import REDACTED_VALUE, is_sensitive_key, redact_text
from langgraph_automation.core.summary import preview_text, summarize_mapping
from langgraph_automation.integrations.artifact.keys import validate_storage_key
from langgraph_automation.integrations.observability import events as obs_events
from langgraph_automation.integrations.observability.base import EventSink
from langgraph_automation.integrations.observability.types import SpanRef

_OBSERVABILITY_MAX_DEPTH = 4
_OBSERVABILITY_MAX_ITEMS = 20
_OBSERVABILITY_MAX_CHARS = 300


def _bounded_text(text: str) -> str:
    return preview_text(redact_text(text), max_chars=_OBSERVABILITY_MAX_CHARS)


def _sanitize_value(value: Any, *, depth: int = 0) -> Any:
    if isinstance(value, str):
        return _bounded_text(value)
    if isinstance(value, Mapping):
        if depth >= _OBSERVABILITY_MAX_DEPTH:
            return REDACTED_VALUE
        sanitized: dict[str, Any] = {}
        for index, (key, nested_value) in enumerate(value.items()):
            if index >= _OBSERVABILITY_MAX_ITEMS:
                break
            key_name = str(key)
            if is_sensitive_key(key_name):
                sanitized[key_name] = REDACTED_VALUE
            else:
                sanitized[key_name] = _sanitize_value(nested_value, depth=depth + 1)
        return sanitized
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        if depth >= _OBSERVABILITY_MAX_DEPTH:
            return [REDACTED_VALUE for _ in list(value)[:_OBSERVABILITY_MAX_ITEMS]]
        return [_sanitize_value(item, depth=depth + 1) for item in list(value)[:_OBSERVABILITY_MAX_ITEMS]]
    return value


def _sanitize_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    return _sanitize_value(dict(value or {}))


def _bounded_summary_text(text: str | None) -> str:
    return _bounded_text(text or '')


def _summary_json(value: Mapping[str, Any] | None) -> str:
    return json.dumps(summarize_mapping(_sanitize_mapping(value)), ensure_ascii=False, sort_keys=True, default=str)


class DjangoEventSink(EventSink):
    '''Persist observability records into Django models.'''

    def _get_run(self, run_id: int) -> Run:
        return Run.objects.get(pk=run_id)

    def _get_span(self, span: SpanRef) -> ExecutionSpan:
        return ExecutionSpan.objects.select_related('run').get(pk=int(span.span_id))

    def _touch_run(self, run: Run, *, span: ExecutionSpan | None = None) -> None:
        run.last_event_at = timezone.now()
        if span is not None:
            run.last_span_name = span.name
            run.save(update_fields=['last_event_at', 'last_span_name', 'updated_at'])
        else:
            run.save(update_fields=['last_event_at', 'updated_at'])

    def _emit_event(
        self,
        run: Run,
        *,
        event_type: str,
        level: str,
        message: str = '',
        payload: Mapping[str, Any] | None = None,
        span: ExecutionSpan | None = None,
        node_name: str = '',
    ) -> RunEvent:
        event = RunEvent.objects.create(
            run=run,
            span=span,
            event_type=event_type,
            level=level,
            node_name=node_name or (span.node_name if span else ''),
            message=_bounded_summary_text(message),
            payload=_sanitize_mapping(payload),
        )
        self._touch_run(run, span=span)
        return event

    def _start_span(
        self,
        *,
        run: Run,
        span_type: str,
        name: str,
        node_name: str = '',
        parent: SpanRef | None = None,
        metadata: Mapping[str, Any] | None = None,
        attempt: int = 1,
    ) -> SpanRef:
        parent_span = self._get_span(parent) if parent is not None else None
        span = ExecutionSpan.objects.create(
            run=run,
            parent=parent_span,
            span_type=span_type,
            name=name,
            status=ExecutionSpanStatus.RUNNING,
            node_name=node_name,
            attempt=attempt,
            started_at=timezone.now(),
            input_summary=_summary_json(metadata),
            metadata=summarize_mapping(_sanitize_mapping(metadata)),
        )
        self._emit_event(
            run,
            event_type=obs_events.SPAN_STARTED,
            level=RunEventLevel.DEBUG,
            message=name,
            payload=_sanitize_mapping(metadata),
            span=span,
            node_name=node_name,
        )
        return SpanRef(span_id=str(span.pk))

    def _complete_span(
        self,
        span_ref: SpanRef,
        *,
        status: str,
        output_summary: str | None = None,
        metrics: Mapping[str, Any] | None = None,
        metadata: Mapping[str, Any] | None = None,
        error_message: str = '',
    ) -> ExecutionSpan:
        span = self._get_span(span_ref)
        now = timezone.now()
        span.status = status
        span.finished_at = now
        if span.started_at is not None:
            span.duration_ms = int((now - span.started_at).total_seconds() * 1000)
        if output_summary is not None:
            span.output_summary = _bounded_summary_text(output_summary)
        if metrics is not None:
            span.metrics = summarize_mapping(_sanitize_mapping(metrics))
        if metadata is not None:
            span.metadata = summarize_mapping(_sanitize_mapping(metadata))
        if error_message:
            span.error_message = _bounded_summary_text(error_message)
        span.save(update_fields=['status', 'finished_at', 'duration_ms', 'output_summary', 'metrics', 'metadata', 'error_message', 'updated_at'])
        self._touch_run(span.run, span=span)
        return span

    @transaction.atomic
    def run_started(self, run_id: int, message: str | None = None, payload: Mapping[str, Any] | None = None) -> RunEvent:
        run = self._get_run(run_id)
        return self._emit_event(run, event_type=obs_events.RUN_STARTED, level=RunEventLevel.INFO, message=message or '', payload=payload)

    @transaction.atomic
    def run_completed(self, run_id: int, message: str | None = None, payload: Mapping[str, Any] | None = None) -> RunEvent:
        run = self._get_run(run_id)
        return self._emit_event(run, event_type=obs_events.RUN_COMPLETED, level=RunEventLevel.INFO, message=message or '', payload=payload)

    @transaction.atomic
    def run_failed(self, run_id: int, error_message: str, payload: Mapping[str, Any] | None = None) -> RunEvent:
        run = self._get_run(run_id)
        return self._emit_event(run, event_type=obs_events.RUN_FAILED, level=RunEventLevel.ERROR, message=error_message, payload=payload)

    @transaction.atomic
    def run_cancelled(self, run_id: int, message: str | None = None, payload: Mapping[str, Any] | None = None) -> RunEvent:
        run = self._get_run(run_id)
        return self._emit_event(run, event_type=obs_events.RUN_CANCELLED, level=RunEventLevel.WARNING, message=message or '', payload=payload)

    @transaction.atomic
    def semantic_event(
        self,
        run_id: int,
        name: str,
        message: str | None = None,
        payload: Mapping[str, Any] | None = None,
        level: str = RunEventLevel.INFO,
        parent_span: SpanRef | None = None,
        node_name: str | None = None,
    ) -> RunEvent:
        run = self._get_run(run_id)
        span_obj = self._get_span(parent_span) if parent_span is not None else None
        return self._emit_event(
            run,
            event_type=obs_events.semantic_event_type(name),
            level=level,
            message=message or name,
            payload=payload,
            span=span_obj,
            node_name=node_name or (span_obj.node_name if span_obj else ''),
        )

    @transaction.atomic
    def span_started(
        self,
        run_id: int,
        span_type: str,
        name: str,
        node_name: str | None = None,
        parent: SpanRef | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> SpanRef:
        run = self._get_run(run_id)
        return self._start_span(run=run, span_type=span_type, name=name, node_name=node_name or '', parent=parent, metadata=metadata)

    @transaction.atomic
    def span_completed(self, span: SpanRef, output_summary: str | None = None, metrics: Mapping[str, Any] | None = None, metadata: Mapping[str, Any] | None = None) -> ExecutionSpan:
        span_obj = self._get_span(span)
        self._emit_event(
            span_obj.run,
            event_type=obs_events.SPAN_COMPLETED,
            level=RunEventLevel.DEBUG,
            message=span_obj.name,
            payload={'output_summary': _bounded_summary_text(output_summary)},
            span=span_obj,
            node_name=span_obj.node_name,
        )
        return self._complete_span(span, status=ExecutionSpanStatus.SUCCEEDED, output_summary=output_summary, metrics=metrics, metadata=metadata)

    @transaction.atomic
    def span_failed(self, span: SpanRef, error_message: str, metrics: Mapping[str, Any] | None = None, metadata: Mapping[str, Any] | None = None) -> ExecutionSpan:
        span_obj = self._get_span(span)
        self._emit_event(
            span_obj.run,
            event_type=obs_events.SPAN_FAILED,
            level=RunEventLevel.ERROR,
            message=error_message,
            payload={'error_message': _bounded_summary_text(error_message)},
            span=span_obj,
            node_name=span_obj.node_name,
        )
        return self._complete_span(span, status=ExecutionSpanStatus.FAILED, metrics=metrics, metadata=metadata, error_message=error_message)

    @transaction.atomic
    def node_started(self, run_id: int, node_name: str, attempt: int = 1, parent: SpanRef | None = None) -> SpanRef:
        run = self._get_run(run_id)
        return self._start_span(run=run, span_type=obs_events.SPAN_NODE, name=node_name, node_name=node_name, parent=parent, attempt=attempt)

    @transaction.atomic
    def node_completed(self, span: SpanRef, output_summary: str | None = None, metrics: Mapping[str, Any] | None = None) -> ExecutionSpan:
        span_obj = self._get_span(span)
        self._emit_event(
            span_obj.run,
            event_type=obs_events.NODE_COMPLETED,
            level=RunEventLevel.DEBUG,
            message=span_obj.name,
            payload={'output_summary': _bounded_summary_text(output_summary)},
            span=span_obj,
            node_name=span_obj.node_name,
        )
        return self._complete_span(span, status=ExecutionSpanStatus.SUCCEEDED, output_summary=output_summary, metrics=metrics)

    @transaction.atomic
    def node_failed(self, span: SpanRef, error_message: str, metrics: Mapping[str, Any] | None = None) -> ExecutionSpan:
        span_obj = self._get_span(span)
        self._emit_event(
            span_obj.run,
            event_type=obs_events.NODE_FAILED,
            level=RunEventLevel.ERROR,
            message=error_message,
            payload={'error_message': _bounded_summary_text(error_message)},
            span=span_obj,
            node_name=span_obj.node_name,
        )
        return self._complete_span(span, status=ExecutionSpanStatus.FAILED, metrics=metrics, error_message=error_message)

    @transaction.atomic
    def llm_started(self, run_id: int, name: str, node_name: str | None = None, parent: SpanRef | None = None, provider: str | None = None, model: str | None = None) -> SpanRef:
        metadata = {'provider': provider, 'model': model} if provider or model else None
        run = self._get_run(run_id)
        return self._start_span(run=run, span_type=obs_events.SPAN_LLM, name=name, node_name=node_name or '', parent=parent, metadata=metadata)

    @transaction.atomic
    def llm_completed(self, span: SpanRef, output_summary: str | None = None, metrics: Mapping[str, Any] | None = None) -> ExecutionSpan:
        span_obj = self._get_span(span)
        self._emit_event(
            span_obj.run,
            event_type=obs_events.LLM_COMPLETED,
            level=RunEventLevel.DEBUG,
            message=span_obj.name,
            payload={'output_summary': _bounded_summary_text(output_summary)},
            span=span_obj,
            node_name=span_obj.node_name,
        )
        return self._complete_span(span, status=ExecutionSpanStatus.SUCCEEDED, output_summary=output_summary, metrics=metrics)

    @transaction.atomic
    def llm_failed(self, span: SpanRef, error_message: str, metrics: Mapping[str, Any] | None = None) -> ExecutionSpan:
        span_obj = self._get_span(span)
        self._emit_event(
            span_obj.run,
            event_type=obs_events.LLM_FAILED,
            level=RunEventLevel.ERROR,
            message=error_message,
            payload={'error_message': _bounded_summary_text(error_message)},
            span=span_obj,
            node_name=span_obj.node_name,
        )
        return self._complete_span(span, status=ExecutionSpanStatus.FAILED, metrics=metrics, error_message=error_message)

    @transaction.atomic
    def tool_started(self, run_id: int, tool_name: str, node_name: str | None = None, parent: SpanRef | None = None) -> SpanRef:
        run = self._get_run(run_id)
        return self._start_span(run=run, span_type=obs_events.SPAN_TOOL, name=tool_name, node_name=node_name or '', parent=parent)

    @transaction.atomic
    def tool_completed(self, span: SpanRef, output_summary: str | None = None, metrics: Mapping[str, Any] | None = None) -> ExecutionSpan:
        span_obj = self._get_span(span)
        self._emit_event(
            span_obj.run,
            event_type=obs_events.TOOL_COMPLETED,
            level=RunEventLevel.DEBUG,
            message=span_obj.name,
            payload={'output_summary': _bounded_summary_text(output_summary)},
            span=span_obj,
            node_name=span_obj.node_name,
        )
        return self._complete_span(span, status=ExecutionSpanStatus.SUCCEEDED, output_summary=output_summary, metrics=metrics)

    @transaction.atomic
    def tool_failed(self, span: SpanRef, error_message: str, metrics: Mapping[str, Any] | None = None) -> ExecutionSpan:
        span_obj = self._get_span(span)
        self._emit_event(
            span_obj.run,
            event_type=obs_events.TOOL_FAILED,
            level=RunEventLevel.ERROR,
            message=error_message,
            payload={'error_message': _bounded_summary_text(error_message)},
            span=span_obj,
            node_name=span_obj.node_name,
        )
        return self._complete_span(span, status=ExecutionSpanStatus.FAILED, metrics=metrics, error_message=error_message)

    @transaction.atomic
    def artifact_created(self, run_id: int, storage_key: str, name: str, kind: str, span: SpanRef | None = None, metadata: Mapping[str, Any] | None = None, content_type: str = '', size: int | None = None) -> Artifact:
        run = self._get_run(run_id)
        span_obj = self._get_span(span) if span is not None else None
        validated_storage_key = validate_storage_key(storage_key)
        artifact = Artifact.objects.create(
            run=run,
            span=span_obj,
            name=name,
            kind=kind,
            storage_key=validated_storage_key,
            content_type=_bounded_summary_text(content_type),
            size=size,
            metadata=_sanitize_mapping(metadata),
        )
        self._emit_event(
            run,
            event_type=obs_events.ARTIFACT_CREATED,
            level=RunEventLevel.INFO,
            message=name,
            payload={'storage_key': validated_storage_key, 'kind': kind},
            span=span_obj,
            node_name=span_obj.node_name if span_obj else '',
        )
        return artifact

    @transaction.atomic
    def checkpoint_saved(self, run_id: int, thread_id: str, checkpoint_id: str, backend: str, span: SpanRef | None = None, state_summary: str | None = None, checkpoint_namespace: str = '') -> CheckpointMetadata:
        run = self._get_run(run_id)
        span_obj = self._get_span(span) if span is not None else None
        checkpoint = CheckpointMetadata.objects.create(
            run=run,
            span=span_obj,
            thread_id=thread_id,
            checkpoint_id=checkpoint_id,
            checkpoint_namespace=_bounded_summary_text(checkpoint_namespace),
            backend=backend,
            node_name=span_obj.node_name if span_obj else '',
            state_summary=_bounded_summary_text(state_summary),
        )
        self._emit_event(
            run,
            event_type=obs_events.CHECKPOINT_SAVED,
            level=RunEventLevel.INFO,
            message=checkpoint_id,
            payload={'backend': backend},
            span=span_obj,
            node_name=span_obj.node_name if span_obj else '',
        )
        return checkpoint
