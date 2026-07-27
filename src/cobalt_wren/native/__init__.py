"""Provisional Native Authoring API.

Native workflows preserve ordinary Python control flow and add orchestration
semantics only at explicit named step boundaries.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Coroutine, Mapping
from dataclasses import dataclass, field
import inspect
import json
import re
from typing import Any, TypeVar, cast

from cobalt_wren.api.errors import (
    WorkflowCancelledError,
    WorkflowTimeoutError,
)
from cobalt_wren.api.plugins import (
    PLUGIN_API_VERSION,
    Plugin,
    PluginContributions,
    PluginMetadata,
)
from cobalt_wren.api.workflow import (
    WorkflowBuildContext,
    WorkflowContribution,
    WorkflowDefinition,
    WorkflowExecutionContext,
    WorkflowExecutionResult,
    WorkflowMetadata,
    WorkflowRequirements,
)
from cobalt_wren.core.summary import summarize_display_value, summarize_mapping
from cobalt_wren.integrations.observability.base import EventSink
from cobalt_wren.integrations.observability.failure_policy import (
    suppress_observability_failure,
)
from cobalt_wren.integrations.observability.types import SpanRef
from cobalt_wren.native.helpers import NativeArtifact
from cobalt_wren.native.schema import infer_workflow_schemas, validate_schema_value
from cobalt_wren.native.policies import NO_RETRY, RetryPolicy

__all__ = [
    "NativeArtifact",
    "NativeWorkflowContext",
    "NativeWorkflow",
    "NativeExecutable",
    "RetryPolicy",
    "workflow",
]

R = TypeVar("R")
_NATIVE_INTEGRATION_ID = "native"
_NATIVE_STEP_SCHEMA = "native.step.v1"
_MAX_STEP_OCCURRENCES = 1_000
_OCCURRENCE_KEY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")


def _required_name(value: str, *, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be blank")
    if len(normalized) > 128:
        raise ValueError(f"{field_name} must be at most 128 characters")
    return normalized


def _occurrence_identity(name: str, occurrence_key: str | None) -> str:
    if occurrence_key is None:
        return name
    normalized = occurrence_key.strip()
    if not _OCCURRENCE_KEY.fullmatch(normalized):
        raise ValueError(
            "occurrence_key must be 1-64 safe identifier characters "
            "(letters, digits, '.', '_', ':', or '-')"
        )
    return f"{name}:{normalized}"


def _summary(value: object) -> object:
    if isinstance(value, Mapping):
        return summarize_mapping(dict(value))
    return summarize_display_value(value)


@dataclass(frozen=True, slots=True)
class _StepStarted:
    symbolic_span: SpanRef
    name: str
    subject_id: str
    logical_sequence: int
    event_sequence: int
    attempt: int
    max_attempts: int
    input_summary: object


@dataclass(frozen=True, slots=True)
class _StepCompleted:
    symbolic_span: SpanRef
    name: str
    subject_id: str
    logical_sequence: int
    event_sequence: int
    attempt: int
    max_attempts: int
    output_summary: object


@dataclass(frozen=True, slots=True)
class _StepFailed:
    symbolic_span: SpanRef
    name: str
    subject_id: str
    logical_sequence: int
    event_sequence: int
    attempt: int
    max_attempts: int
    status: str
    error_message: str


_BufferedOperation = _StepStarted | _StepCompleted | _StepFailed


@dataclass(slots=True)
class _NativeObservationBuffer:
    operations: list[_BufferedOperation] = field(default_factory=list)
    _span_counter: int = 0
    _event_counter: int = 0

    def _next_event_sequence(self) -> int:
        self._event_counter += 1
        return self._event_counter

    def start(
        self,
        name: str,
        *,
        subject_id: str,
        logical_sequence: int,
        attempt: int,
        max_attempts: int,
        input_value: object,
    ) -> SpanRef:
        self._span_counter += 1
        span = SpanRef(span_id=f"native-buffer-{self._span_counter}")
        self.operations.append(
            _StepStarted(
                symbolic_span=span,
                name=name,
                subject_id=subject_id,
                logical_sequence=logical_sequence,
                event_sequence=self._next_event_sequence(),
                attempt=attempt,
                max_attempts=max_attempts,
                input_summary=_summary(input_value),
            )
        )
        return span

    def complete(
        self,
        span: SpanRef,
        *,
        name: str,
        subject_id: str,
        logical_sequence: int,
        attempt: int,
        max_attempts: int,
        output_value: object,
    ) -> None:
        self.operations.append(
            _StepCompleted(
                symbolic_span=span,
                name=name,
                subject_id=subject_id,
                logical_sequence=logical_sequence,
                event_sequence=self._next_event_sequence(),
                attempt=attempt,
                max_attempts=max_attempts,
                output_summary=_summary(output_value),
            )
        )

    def fail(
        self,
        span: SpanRef,
        *,
        name: str,
        subject_id: str,
        logical_sequence: int,
        attempt: int,
        max_attempts: int,
        retrying: bool,
    ) -> None:
        self.operations.append(
            _StepFailed(
                symbolic_span=span,
                name=name,
                subject_id=subject_id,
                logical_sequence=logical_sequence,
                event_sequence=self._next_event_sequence(),
                attempt=attempt,
                max_attempts=max_attempts,
                status="retrying" if retrying else "failed",
                error_message="Native step execution failed.",
            )
        )

    def replay(self, sink: EventSink | None, context: WorkflowExecutionContext) -> None:
        if sink is None or not isinstance(context.run_id, int):
            return
        actual_spans: dict[str, SpanRef] = {}
        for operation in self.operations:
            if isinstance(operation, _StepStarted):
                actual = _start_span(sink, context, operation)
                if actual is not None:
                    actual_spans[operation.symbolic_span.span_id] = actual
                _emit_step_projection(
                    sink,
                    context,
                    span=actual,
                    operation=operation,
                    status="running",
                    input_summary=operation.input_summary,
                )
                continue
            actual = actual_spans.get(operation.symbolic_span.span_id)
            if isinstance(operation, _StepCompleted):
                _complete_span(sink, actual, operation)
                _emit_step_projection(
                    sink,
                    context,
                    span=actual,
                    operation=operation,
                    status="succeeded",
                    output_summary=operation.output_summary,
                )
            else:
                _fail_span(sink, actual, operation)
                _emit_step_projection(
                    sink,
                    context,
                    span=actual,
                    operation=operation,
                    status=operation.status,
                    error_message=operation.error_message,
                )


@dataclass(slots=True)
class NativeWorkflowContext:
    """Per-execution Native context exposed to workflow authors."""

    build: WorkflowBuildContext
    execution: WorkflowExecutionContext
    _observations: _NativeObservationBuffer = field(
        default_factory=_NativeObservationBuffer,
        repr=False,
    )
    _sequence: int = 0
    _subjects: set[str] = field(default_factory=set, repr=False)
    _progress_current: float | None = field(default=None, repr=False)
    _progress_total: float | None = field(default=None, repr=False)
    _metric_names: set[str] = field(default_factory=set, repr=False)

    async def step(
        self,
        name: str,
        function: Callable[..., R] | Callable[..., Awaitable[R]],
        /,
        *args: object,
        retry: RetryPolicy | None = None,
        timeout_seconds: float | None = None,
        occurrence_key: str | None = None,
        **kwargs: object,
    ) -> R:
        """Run an ordinary sync or async callable as an observed named step."""

        step_name = _required_name(name, field_name="step name")
        subject_id = _occurrence_identity(step_name, occurrence_key)
        if subject_id in self._subjects:
            raise ValueError(
                f"Native step occurrence {subject_id!r} was already used; "
                "provide a unique occurrence_key for repeated calls"
            )
        if len(self._subjects) >= _MAX_STEP_OCCURRENCES:
            raise RuntimeError("Native workflow exceeded the step occurrence limit")
        if timeout_seconds is not None and (
            isinstance(timeout_seconds, bool) or timeout_seconds <= 0
        ):
            raise ValueError("timeout_seconds must be a positive number")

        self.check_cancelled()
        self._subjects.add(subject_id)
        self._sequence += 1
        logical_sequence = self._sequence
        policy = retry or NO_RETRY
        input_value = {"args": args, "kwargs": kwargs}

        for attempt in range(1, policy.max_attempts + 1):
            self.check_cancelled()
            symbolic_span = self._observations.start(
                step_name,
                subject_id=subject_id,
                logical_sequence=logical_sequence,
                attempt=attempt,
                max_attempts=policy.max_attempts,
                input_value=input_value,
            )
            try:
                result = await _invoke_step(
                    function,
                    args,
                    kwargs,
                    timeout_seconds=_effective_timeout(
                        timeout_seconds,
                        self.execution,
                    ),
                )
                self.check_cancelled()
            except Exception as exc:
                retrying = (
                    not isinstance(exc, WorkflowCancelledError)
                    and policy.should_retry(exc, attempt=attempt)
                )
                self._observations.fail(
                    symbolic_span,
                    name=step_name,
                    subject_id=subject_id,
                    logical_sequence=logical_sequence,
                    attempt=attempt,
                    max_attempts=policy.max_attempts,
                    retrying=retrying,
                )
                if not retrying:
                    try:
                        exc.add_note(
                            f"Native step {step_name!r} failed on attempt "
                            f"{attempt} of {policy.max_attempts}."
                        )
                    except AttributeError:
                        pass
                    raise
                await self._retry_delay(policy.delay_after(attempt))
                continue
            self._observations.complete(
                symbolic_span,
                name=step_name,
                subject_id=subject_id,
                logical_sequence=logical_sequence,
                attempt=attempt,
                max_attempts=policy.max_attempts,
                output_value=result,
            )
            return result
        raise AssertionError("retry loop exhausted without returning or raising")

    async def _retry_delay(self, delay_seconds: float) -> None:
        remaining = delay_seconds
        while remaining > 0:
            self.check_cancelled()
            interval = min(remaining, 0.1)
            await asyncio.sleep(interval)
            remaining -= interval
        self.check_cancelled()

    def check_cancelled(self) -> None:
        if self.execution.control is not None:
            self.execution.control.check()

    def require_provider(self, profile_name: str) -> object:
        return self.build.require_provider(profile_name)

    def require_tool(self, tool_name: str) -> object:
        return self.build.require_tool(tool_name)

    def require_artifact_store(self) -> object:
        return self.build.require_artifact_store()

    @property
    def llm(self):
        from cobalt_wren.native.helpers import NativeLLMHelper

        return NativeLLMHelper(self)

    @property
    def tool(self):
        from cobalt_wren.native.helpers import NativeToolHelper

        return NativeToolHelper(self)

    @property
    def progress(self):
        from cobalt_wren.native.helpers import NativeProgressHelper

        return NativeProgressHelper(self)

    @property
    def metric(self):
        from cobalt_wren.native.helpers import NativeMetricHelper

        return NativeMetricHelper(self)

    @property
    def artifact(self):
        from cobalt_wren.native.helpers import NativeArtifactHelper

        return NativeArtifactHelper(self)


NativeWorkflowFunction = Callable[
    [NativeWorkflowContext, Mapping[str, object]],
    object | Awaitable[object],
]


@dataclass(frozen=True, slots=True)
class NativeWorkflow:
    """Decorated Native workflow metadata and conversion surface."""

    name: str
    function: NativeWorkflowFunction
    description: str = ""
    version: str = "0.1.0"
    tags: tuple[str, ...] = ()
    input_schema: Mapping[str, object] | None = None
    output_schema: Mapping[str, object] | None = None
    requirements: WorkflowRequirements = field(default_factory=WorkflowRequirements)

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _required_name(self.name, field_name="workflow name"))
        object.__setattr__(self, "tags", tuple(self.tags))
        object.__setattr__(self, "input_schema", None if self.input_schema is None else dict(self.input_schema))
        object.__setattr__(self, "output_schema", None if self.output_schema is None else dict(self.output_schema))
        if not isinstance(self.requirements, WorkflowRequirements):
            raise TypeError("requirements must be a WorkflowRequirements")

    def contribution(
        self,
        *,
        kind: str,
        requirements: WorkflowRequirements | None = None,
        input_schema: Mapping[str, object] | None = None,
        output_schema: Mapping[str, object] | None = None,
    ) -> WorkflowContribution:
        workflow_kind = _required_name(kind, field_name="workflow kind")

        def build(context: WorkflowBuildContext) -> object:
            from cobalt_wren.integrations.native import (
                integrate_native_workflow,
            )

            return integrate_native_workflow(
                self,
                workflow_kind=workflow_kind,
                build_context=context,
            )

        return WorkflowContribution(
            kind=workflow_kind,
            definition=WorkflowDefinition(
                kind=workflow_kind,
                metadata=WorkflowMetadata(
                    name=self.name,
                    description=self.description,
                    version=self.version,
                    tags=(*self.tags, "native"),
                    metadata={"authoring": "native"},
                ),
                requirements=requirements or self.requirements,
                build=build,
                input_schema=input_schema or self.input_schema,
                output_schema=output_schema or self.output_schema,
                extra={
                    "integration_id": _NATIVE_INTEGRATION_ID,
                    "lifecycle_events_owner": "control_plane",
                },
            ),
            metadata={"authoring": "native"},
        )

    def plugin(
        self,
        *,
        plugin_name: str,
        workflow_kind: str,
        plugin_version: str = "0.1.0",
        requirements: WorkflowRequirements | None = None,
        input_schema: Mapping[str, object] | None = None,
        output_schema: Mapping[str, object] | None = None,
    ) -> Plugin:
        contribution = self.contribution(
            kind=workflow_kind,
            requirements=requirements,
            input_schema=input_schema,
            output_schema=output_schema,
        )
        return Plugin(
            metadata=PluginMetadata(
                name=_required_name(plugin_name, field_name="plugin name"),
                version=plugin_version,
                plugin_types=("workflow",),
                provides={"workflows": (workflow_kind,)},
                metadata={"plugin_api_version": PLUGIN_API_VERSION},
            ),
            contributions=PluginContributions(workflows=(contribution,)),
        )


@dataclass(frozen=True, slots=True)
class NativeExecutable:
    workflow: NativeWorkflow
    build_context: WorkflowBuildContext

    def execute(
        self,
        input_payload: Mapping[str, object],
        *,
        context: WorkflowExecutionContext,
    ) -> WorkflowExecutionResult:
        validate_schema_value(
            dict(input_payload), self.workflow.input_schema, phase="input"
        )
        native_context = NativeWorkflowContext(
            build=self.build_context,
            execution=context,
        )
        result: object | None = None
        error: Exception | None = None
        try:
            result = _run_awaitable(
                _invoke_workflow(self.workflow.function, native_context, input_payload)
            )
        except Exception as exc:
            error = exc
        sink = cast(EventSink | None, context.event_sink)
        native_context._observations.replay(sink, context)
        if error is not None:
            raise error
        output = _normalize_output(result)
        validate_schema_value(output, self.workflow.output_schema, phase="output")
        return WorkflowExecutionResult(
            output=output,
            metadata={
                "integration_id": _NATIVE_INTEGRATION_ID,
                "workflow_name": self.workflow.name,
                "step_count": native_context._sequence,
                "attempt_count": sum(
                    isinstance(operation, _StepStarted)
                    for operation in native_context._observations.operations
                ),
                "last_step_name": _last_step_name(native_context._observations),
            },
        )


def workflow(
    name: str | None = None,
    *,
    description: str = "",
    version: str = "0.1.0",
    tags: tuple[str, ...] = (),
    input_schema: Mapping[str, object] | None = None,
    output_schema: Mapping[str, object] | None = None,
    provider_profiles: tuple[str, ...] = (),
    tools: tuple[str, ...] = (),
    artifact_store: bool = False,
    event_sinks: tuple[str, ...] = (),
) -> Callable[[NativeWorkflowFunction], NativeWorkflow]:
    """Attach Native workflow metadata without rewriting Python control flow."""

    def decorate(function: NativeWorkflowFunction) -> NativeWorkflow:
        inferred_input, inferred_output = infer_workflow_schemas(function)
        return NativeWorkflow(
            name=name or function.__name__.replace("_", " ").title(),
            function=function,
            description=description,
            version=version,
            tags=tags,
            input_schema=input_schema or inferred_input,
            output_schema=output_schema or inferred_output,
            requirements=WorkflowRequirements(
                provider_profiles=provider_profiles,
                tools=tools,
                artifact_store=artifact_store,
                event_sinks=event_sinks,
            ),
        )

    return decorate


async def _invoke_workflow(
    function: NativeWorkflowFunction,
    context: NativeWorkflowContext,
    input_payload: Mapping[str, object],
) -> object:
    result = function(context, dict(input_payload))
    if inspect.isawaitable(result):
        return await cast(Awaitable[object], result)
    return result


async def _invoke_step(
    function: Callable[..., R] | Callable[..., Awaitable[R]],
    args: tuple[object, ...],
    kwargs: Mapping[str, object],
    *,
    timeout_seconds: float | None,
) -> R:
    if inspect.iscoroutinefunction(function):
        invocation = cast(Callable[..., Awaitable[R]], function)(*args, **kwargs)
    else:
        invocation = asyncio.to_thread(
            cast(Callable[..., R], function),
            *args,
            **kwargs,
        )
    try:
        if timeout_seconds is None:
            return await invocation
        return await asyncio.wait_for(invocation, timeout=timeout_seconds)
    except TimeoutError as exc:
        raise WorkflowTimeoutError("Native step execution timed out.") from exc


def _effective_timeout(
    requested: float | None,
    execution: WorkflowExecutionContext,
) -> float | None:
    control = execution.control
    remaining = None if control is None else control.remaining_seconds
    if control is not None and remaining is not None and remaining <= 0:
        control.check()
    if requested is None:
        return remaining
    if remaining is None:
        return float(requested)
    return min(float(requested), remaining)


def _run_awaitable(awaitable: Coroutine[Any, Any, object]) -> object:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(awaitable)
    raise RuntimeError(
        "NativeExecutable.execute() cannot run inside an active event loop; "
        "invoke it through the synchronous workflow execution boundary."
    )


def _normalize_output(result: object) -> dict[str, object]:
    if isinstance(result, WorkflowExecutionResult):
        return dict(result.output)
    if isinstance(result, Mapping):
        return dict(result)
    if result is None:
        return {}
    return {"result": result}


def _last_step_name(buffer: _NativeObservationBuffer) -> str:
    terminal = [
        operation.name
        for operation in buffer.operations
        if isinstance(operation, (_StepCompleted, _StepFailed))
        and not (
            isinstance(operation, _StepFailed)
            and operation.status == "retrying"
        )
    ]
    return terminal[-1] if terminal else ""


def _start_span(
    sink: EventSink,
    context: WorkflowExecutionContext,
    operation: _StepStarted,
) -> SpanRef | None:
    if not isinstance(context.run_id, int):
        return None
    try:
        return sink.span_started(
            context.run_id,
            span_type="step",
            name=operation.name,
            node_name=operation.name,
            parent=cast(SpanRef | None, context.parent_span),
            metadata={
                "integration_id": _NATIVE_INTEGRATION_ID,
                "subject_external_id": operation.subject_id,
                "sequence": operation.logical_sequence,
                "attempt": operation.attempt,
                "max_attempts": operation.max_attempts,
                "input_summary": operation.input_summary,
            },
        )
    except Exception:
        return None


def _complete_span(
    sink: EventSink,
    span: SpanRef | None,
    operation: _StepCompleted,
) -> None:
    if span is None:
        return
    suppress_observability_failure(
        lambda: sink.span_completed(
            span,
            output_summary=json.dumps(
                operation.output_summary,
                ensure_ascii=False,
                sort_keys=True,
                default=str,
            ),
            metrics={"ok": True, "attempt": operation.attempt},
            metadata={
                "integration_id": _NATIVE_INTEGRATION_ID,
                "subject_external_id": operation.subject_id,
                "sequence": operation.logical_sequence,
                "attempt": operation.attempt,
                "max_attempts": operation.max_attempts,
            },
        ),
        context={"component": "native", "operation": "step_completed"},
    )


def _fail_span(
    sink: EventSink,
    span: SpanRef | None,
    operation: _StepFailed,
) -> None:
    if span is None:
        return
    suppress_observability_failure(
        lambda: sink.span_failed(
            span,
            error_message=operation.error_message,
            metrics={
                "ok": False,
                "attempt": operation.attempt,
                "retrying": operation.status == "retrying",
            },
            metadata={
                "integration_id": _NATIVE_INTEGRATION_ID,
                "subject_external_id": operation.subject_id,
                "sequence": operation.logical_sequence,
                "attempt": operation.attempt,
                "max_attempts": operation.max_attempts,
                "terminal_status": operation.status,
            },
        ),
        context={"component": "native", "operation": "step_failed"},
    )


def _emit_step_projection(
    sink: EventSink,
    context: WorkflowExecutionContext,
    *,
    span: SpanRef | None,
    operation: _BufferedOperation,
    status: str,
    input_summary: object | None = None,
    output_summary: object | None = None,
    error_message: str = "",
) -> None:
    callback = getattr(sink, "integration_projection", None)
    if not callable(callback) or not isinstance(context.run_id, int):
        return
    payload: dict[str, object] = {
        "step_name": operation.name,
        "occurrence_id": operation.subject_id,
        "status": status,
        "attempt": operation.attempt,
        "max_attempts": operation.max_attempts,
        "logical_sequence": operation.logical_sequence,
    }
    if input_summary is not None:
        payload["input_summary"] = input_summary
    if output_summary is not None:
        payload["output_summary"] = output_summary
    if error_message:
        payload["error"] = error_message
    suppress_observability_failure(
        lambda: callback(
            context.run_id,
            integration_id=_NATIVE_INTEGRATION_ID,
            schema_id=_NATIVE_STEP_SCHEMA,
            owner_kind="execution_unit",
            owner_external_id=operation.subject_id,
            title=f"Native step: {operation.name}",
            payload=payload,
            span=span,
            retention_class="execution_detail",
            classification="internal",
            projection_kind="snapshot",
            subject_kind="execution_unit",
            subject_external_id=operation.subject_id,
            sequence=operation.event_sequence,
        ),
        context={
            "component": "native",
            "operation": "integration_projection",
            "schema_id": _NATIVE_STEP_SCHEMA,
        },
    )
