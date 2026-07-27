"""Renderer-facing projection for live Run observability."""
from __future__ import annotations
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from django.utils import timezone
from cobalt_wren.apps.automation.models.event import RunEvent
from cobalt_wren.apps.automation.models.execution import ExecutionSpan, ExecutionSpanStatus, ExecutionSpanType
from cobalt_wren.apps.automation.models.job import ExecutionJob, ExecutionJobStatus
from cobalt_wren.apps.automation.models.run import Run, RunStatus
from cobalt_wren.apps.automation.ui.formatters import format_value
from cobalt_wren.apps.automation.ui.specs import ValueSpec
from cobalt_wren.apps.automation.ui.values import build_value_spec
from cobalt_wren.apps.automation.ui.redaction import redact_value

@dataclass(frozen=True)
class RunTimelineItemSpec:
    name: str
    span_type: str
    status: str
    attempt: int
    duration: str
    started_at: str
    depth: int
    url: str

@dataclass(frozen=True)
class RunLLMMessageSpec:
    role: str
    preview: str

@dataclass(frozen=True)
class RunLLMInteractionSpec:
    node_name: str
    provider: str
    model: str
    status: str
    attempt: int
    messages: tuple[RunLLMMessageSpec, ...]
    prompt_preview: str
    response_preview: str
    input_tokens: str
    output_tokens: str
    duration: str
    url: str

@dataclass(frozen=True)
class RunProgressSpec:
    current: str
    total: str
    percent: str
    message: str


@dataclass(frozen=True)
class RunMetricSpec:
    name: str
    value: str
    unit: str


@dataclass(frozen=True)
class RunNodeOutputSpec:
    node_name: str
    status: str
    output_preview: str
    url: str



@dataclass(frozen=True)
class RunFailureDiagnosticSpec:
    error_message: str
    failed_activity: str
    span_type: str
    attempt: int
    failed_span_url: str
    last_successful_activity: str
    input_value: ValueSpec | None
    event_type: str
    event_message: str
    event_value: ValueSpec | None

@dataclass(frozen=True)
class RunLiveSpec:
    run_id: int
    revision: str
    status: str
    terminal: bool
    fragment_url: str
    stream_url: str
    current_activity: str
    elapsed: str
    last_update: str
    heartbeat: str
    completed_steps: int
    total_steps: int
    last_event_type: str
    last_event_message: str
    timeline: tuple[RunTimelineItemSpec, ...]
    llm_interactions: tuple[RunLLMInteractionSpec, ...]
    node_output: RunNodeOutputSpec | None
    progress: RunProgressSpec | None
    metrics: tuple[RunMetricSpec, ...]
    failure: RunFailureDiagnosticSpec | None

def _format_duration(milliseconds: int | None) -> str:
    if milliseconds is None:
        return "—"
    seconds = milliseconds / 1000
    if seconds < 1:
        return f"{milliseconds} ms"
    if seconds < 60:
        return f"{seconds:.1f} s"
    minutes, remainder = divmod(int(seconds), 60)
    return f"{minutes}m {remainder}s"

def _format_elapsed(run: Run, now: datetime) -> str:
    start = run.started_at or run.created_at
    end = run.finished_at if run.is_terminal_state and run.finished_at else now
    seconds = max(0, int((end - start).total_seconds()))
    minutes, remainder = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes}m {remainder}s"
    if minutes:
        return f"{minutes}m {remainder}s"
    return f"{remainder}s"

def _safe_text(field_name: str, value: object) -> str:
    safe_value, _redacted = redact_value(field_name, value)
    return format_value(safe_value)

def _json_mapping(value: str) -> Mapping[str, object]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, Mapping) else {}

def _deep_preview(value: object) -> str | None:
    if isinstance(value, Mapping):
        preview = value.get("preview")
        if isinstance(preview, str) and preview:
            return preview
        if preview is not None:
            nested_preview = _deep_preview(preview)
            if nested_preview:
                return nested_preview
        for nested in value.values():
            found = _deep_preview(nested)
            if found:
                return found
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for nested in value:
            found = _deep_preview(nested)
            if found:
                return found
    return None

def _summary_text(value: str) -> str:
    parsed = _json_mapping(value)
    found = _deep_preview(parsed)
    if found:
        return _safe_text("preview", found)
    return _safe_text("preview", value) if value else ""

def _mapping_scalar(value: Mapping[str, object], key: str) -> str:
    direct = value.get(key)
    if direct not in (None, "") and not isinstance(direct, (Mapping, list, tuple)):
        return _safe_text(key, direct)
    preview = value.get("preview")
    if isinstance(preview, Mapping):
        found = preview.get(key)
        if found not in (None, "") and not isinstance(found, (Mapping, list, tuple)):
            return _safe_text(key, found)
    for nested in value.values():
        if isinstance(nested, Mapping):
            found = _mapping_scalar(nested, key)
            if found != "—":
                return found
    return "—"

def _numeric_metric(value: Mapping[str, object], key: str) -> str:
    preview = value.get("preview")
    if isinstance(preview, Mapping):
        found = preview.get(key)
        if isinstance(found, (int, float)) and not isinstance(found, bool):
            return format_value(found)
    for nested in value.values():
        if isinstance(nested, Mapping):
            found = _numeric_metric(nested, key)
            if found != "—":
                return found
    return "—"

def _message_candidate(value: object) -> RunLLMMessageSpec | None:
    if not isinstance(value, Mapping):
        return None
    role = _mapping_scalar(value, "role")
    preview = _mapping_scalar(value, "preview")
    if role == "—" or preview == "—":
        return None
    return RunLLMMessageSpec(role=role, preview=preview)

def _find_messages(value: object) -> tuple[RunLLMMessageSpec, ...]:
    if isinstance(value, Mapping):
        for key in ("message_previews", "messages"):
            nested = value.get(key)
            if isinstance(nested, Sequence) and not isinstance(nested, (str, bytes, bytearray)):
                messages = tuple(message for item in nested if (message := _message_candidate(item)) is not None)
                if messages and all(message.role != "***TRUNCATED***" for message in messages):
                    return messages
        for nested in value.values():
            found = _find_messages(nested)
            if found:
                return found
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for nested in value:
            found = _find_messages(nested)
            if found:
                return found
    return ()

def _span_depth(span: ExecutionSpan, by_id: dict[int, ExecutionSpan]) -> int:
    depth = 0
    parent_id = span.parent_id
    visited: set[int] = set()
    while parent_id is not None and parent_id not in visited and depth < 8:
        visited.add(parent_id)
        depth += 1
        parent = by_id.get(parent_id)
        parent_id = parent.parent_id if parent is not None else None
    return depth

def _current_activity(run: Run, current_span: ExecutionSpan | None, active_job: ExecutionJob | None) -> str:
    if current_span is not None:
        return current_span.node_name or current_span.name
    if run.status == RunStatus.WAITING:
        return "Waiting for workflow action"
    if active_job is not None and active_job.status == ExecutionJobStatus.QUEUED:
        return "Queued for worker execution"
    if run.last_span_name:
        return run.last_span_name
    return run.get_status_display()

def _llm_interaction(span: ExecutionSpan) -> RunLLMInteractionSpec:
    metadata = span.metadata if isinstance(span.metadata, Mapping) else {}
    metrics = span.metrics if isinstance(span.metrics, Mapping) else {}
    input_mapping = _json_mapping(span.input_summary)
    return RunLLMInteractionSpec(
        node_name=_safe_text("node_name", span.node_name or span.name),
        provider=_mapping_scalar(metadata, "provider"),
        model=_mapping_scalar(metadata, "model"),
        status=span.get_status_display(),
        attempt=span.attempt,
        messages=_find_messages(input_mapping),
        prompt_preview=_summary_text(span.input_summary),
        response_preview=_summary_text(span.output_summary),
        input_tokens=_numeric_metric(metrics, "input_tokens"),
        output_tokens=_numeric_metric(metrics, "output_tokens"),
        duration=_format_duration(span.duration_ms),
        url=f"/ui/spans/{span.pk}/",
    )

def _node_output(spans: list[ExecutionSpan]) -> RunNodeOutputSpec | None:
    span = next((item for item in reversed(spans) if item.span_type == ExecutionSpanType.NODE and item.output_summary), None)
    if span is None:
        return None
    return RunNodeOutputSpec(
        node_name=_safe_text("node_name", span.node_name or span.name),
        status=span.get_status_display(),
        output_preview=_summary_text(span.output_summary),
        url=f"/ui/spans/{span.pk}/",
    )



def _summary_value(value: str) -> ValueSpec | None:
    if not value:
        return None
    parsed = _json_mapping(value)
    projected: object = parsed if parsed else value
    spec = build_value_spec(projected)
    if spec.kind == "empty" or (spec.kind in {"mapping", "list"} and spec.count == 0):
        return None
    return spec


def _failure_diagnostic(run: Run, spans: list[ExecutionSpan]) -> RunFailureDiagnosticSpec | None:
    if run.status not in {RunStatus.FAILED, RunStatus.TIMED_OUT, RunStatus.CANCELLED}:
        return None
    failed_span = next((span for span in reversed(spans) if span.status == ExecutionSpanStatus.FAILED), None)
    if failed_span is None:
        return None
    previous_success = next(
        (span for span in reversed(spans) if span.created_at < failed_span.created_at and span.status == ExecutionSpanStatus.SUCCEEDED),
        None,
    )
    failure_event = (
        RunEvent.objects.filter(run=run, span=failed_span, level="error")
        .order_by("-created_at", "-pk")
        .first()
    )
    event_value = None
    if failure_event is not None and isinstance(failure_event.payload_summary, Mapping):
        event_value = build_value_spec(failure_event.payload_summary)
        if event_value.kind == "empty" or (event_value.kind in {"mapping", "list"} and event_value.count == 0):
            event_value = None
    return RunFailureDiagnosticSpec(
        error_message=_safe_text("error_message", failed_span.error_message or run.error_message),
        failed_activity=_safe_text("node_name", failed_span.node_name or failed_span.name),
        span_type=failed_span.get_span_type_display(),
        attempt=failed_span.attempt,
        failed_span_url=f"/ui/spans/{failed_span.pk}/",
        last_successful_activity=(
            _safe_text("node_name", previous_success.node_name or previous_success.name) if previous_success is not None else "None recorded"
        ),
        input_value=_summary_value(failed_span.input_summary),
        event_type=_safe_text("event_type", failure_event.event_type) if failure_event is not None else "No failure event recorded",
        event_message=_safe_text("message", failure_event.message) if failure_event is not None else "",
        event_value=event_value,
    )

def _native_progress_and_metrics(run: Run) -> tuple[RunProgressSpec | None, tuple[RunMetricSpec, ...]]:
    events = list(
        RunEvent.objects.filter(
            run=run, event_type__in=["semantic.native.progress", "semantic.native.metric"]
        ).order_by("created_at", "pk")
    )
    progress = None
    metrics: dict[str, RunMetricSpec] = {}
    for event in events:
        payload = event.payload if isinstance(event.payload, Mapping) else {}
        if event.event_type == "semantic.native.progress":
            progress = RunProgressSpec(
                current=_safe_text("current", payload.get("current", "—")),
                total=_safe_text("total", payload.get("total", "—")),
                percent=_safe_text("percent", payload.get("percent", "—")),
                message=_safe_text("message", event.message),
            )
        else:
            name = str(payload.get("name", "")).strip()
            if name:
                metrics[name] = RunMetricSpec(
                    name=_safe_text("name", name),
                    value=_safe_text("value", payload.get("value", "—")),
                    unit=_safe_text("unit", payload.get("unit", "")),
                )
    return progress, tuple(list(metrics.values())[-50:])


def _revision(run: Run, spans: list[ExecutionSpan], last_event: RunEvent | None, latest_job: ExecutionJob | None) -> str:
    payload = {
        "run": [run.status, run.updated_at.isoformat(), run.last_event_at.isoformat() if run.last_event_at else ""],
        "spans": [[span.pk, span.status, span.updated_at.isoformat(), span.attempt] for span in spans],
        "event": [last_event.pk, last_event.created_at.isoformat()] if last_event is not None else [],
        "job": [latest_job.pk, latest_job.status, latest_job.updated_at.isoformat(), latest_job.heartbeat_at.isoformat() if latest_job.heartbeat_at else ""] if latest_job is not None else [],
    }
    encoded = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()[:16]

def build_run_live_spec(run_id: int, *, actor: object | None = None) -> RunLiveSpec:
    """Project stable control-plane records without inspecting workflow internals."""
    del actor
    run = Run.objects.select_related("workflow").filter(pk=run_id).first()
    if run is None:
        raise LookupError(f"Run {run_id} was not found")
    spans = list(ExecutionSpan.objects.filter(run=run).select_related("parent").order_by("created_at", "pk"))
    current_span = next((span for span in reversed(spans) if span.status == ExecutionSpanStatus.RUNNING), None)
    last_event = RunEvent.objects.filter(run=run).order_by("-created_at", "-pk").first()
    active_job = ExecutionJob.objects.filter(run=run, status__in=[ExecutionJobStatus.QUEUED, ExecutionJobStatus.CLAIMED]).order_by("-created_at", "-pk").first()
    latest_job = active_job or ExecutionJob.objects.filter(run=run).order_by("-created_at", "-pk").first()
    by_id = {span.pk: span for span in spans if span.pk is not None}
    progress, metrics = _native_progress_and_metrics(run)
    timeline = tuple(RunTimelineItemSpec(name=_safe_text("name", span.node_name or span.name), span_type=span.get_span_type_display(), status=span.get_status_display(), attempt=span.attempt, duration=_format_duration(span.duration_ms), started_at=format_value(span.started_at or span.created_at), depth=_span_depth(span, by_id), url=f"/ui/spans/{span.pk}/") for span in spans)
    completed_statuses = {ExecutionSpanStatus.SUCCEEDED, ExecutionSpanStatus.FAILED, ExecutionSpanStatus.CANCELLED, ExecutionSpanStatus.SKIPPED}
    last_update_at = run.last_event_at or run.updated_at
    heartbeat_at = latest_job.heartbeat_at if latest_job is not None else None
    return RunLiveSpec(
        run_id=run.pk,
        revision=_revision(run, spans, last_event, latest_job),
        status=run.get_status_display(),
        terminal=run.is_terminal_state,
        fragment_url=f"/ui/runs/{run.pk}/live/",
        stream_url=f"/ui/runs/{run.pk}/stream/",
        current_activity=_safe_text("current_activity", _current_activity(run, current_span, active_job)),
        elapsed=_format_elapsed(run, timezone.now()),
        last_update=format_value(last_update_at),
        heartbeat=format_value(heartbeat_at) if heartbeat_at else "Not reported",
        completed_steps=sum(span.status in completed_statuses for span in spans),
        total_steps=len(spans),
        last_event_type=_safe_text("event_type", last_event.event_type if last_event is not None else "No events yet"),
        last_event_message=_safe_text("message", last_event.message if last_event is not None else ""),
        timeline=timeline,
        llm_interactions=tuple(_llm_interaction(span) for span in spans if span.span_type == ExecutionSpanType.LLM),
        node_output=_node_output(spans),
        progress=progress,
        metrics=metrics,
        failure=_failure_diagnostic(run, spans),
    )
