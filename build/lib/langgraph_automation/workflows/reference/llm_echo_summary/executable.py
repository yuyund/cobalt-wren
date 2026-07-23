"""Public executable implementation for the reference workflow."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
from typing import Any, cast

from langgraph.graph import END, START, StateGraph

from langgraph_automation.api.workflow import WorkflowExecutionContext, WorkflowExecutionResult
from langgraph_automation.core.summary import summarize_mapping
from langgraph_automation.integrations.llm.base import LLMClient
from langgraph_automation.integrations.llm.observed_client import ObservedLLMClient
from langgraph_automation.integrations.observability import events as obs_events
from langgraph_automation.integrations.observability.base import EventSink
from langgraph_automation.integrations.observability.failure_policy import suppress_observability_failure
from langgraph_automation.integrations.observability.types import ObservabilityContext, SpanRef
from langgraph_automation.integrations.tools.base import ToolCallable
from langgraph_automation.integrations.tools.observed_registry import ObservedToolRegistry
from langgraph_automation.integrations.tools.policy import AllowlistToolPolicy, ToolPolicyContext
from langgraph_automation.integrations.tools.policy_registry import PolicyAwareToolRegistry
from langgraph_automation.integrations.tools.registry import InMemoryToolRegistry
from langgraph_automation.integrations.tools.policy import POLICY_DENIED_EXIT_CODE

from .state import LlmEchoSummaryState


@dataclass(frozen=True, slots=True)
class LlmEchoSummaryExecutable:
    llm_client: LLMClient
    echo_tool: ToolCallable
    allowed_tools: tuple[str, ...] = ("echo",)

    def execute(
        self,
        input_payload: Mapping[str, object],
        *,
        context: WorkflowExecutionContext,
    ) -> WorkflowExecutionResult:
        text = _primary_text(input_payload)
        event_sink = cast(EventSink | None, context.event_sink)
        parent_span = cast(SpanRef | None, context.parent_span)
        base_observability = ObservabilityContext(
            run_id=context.run_id,
            thread_id=context.thread_id,
            parent_span=parent_span,
            node_name="workflow",
        )
        observed_llm = ObservedLLMClient(
            inner=self.llm_client,
            event_sink=event_sink,
            observability=base_observability,
        )
        registry = InMemoryToolRegistry()
        registry.register("echo", self.echo_tool)
        policy_registry = PolicyAwareToolRegistry(
            inner=registry,
            policy=AllowlistToolPolicy(allowed_tools=frozenset(self.allowed_tools)),
            context=ToolPolicyContext(
                run_id=context.run_id,
                workflow_id=None,
                thread_id=context.thread_id,
            ),
        )
        observed_tools = ObservedToolRegistry(
            inner=policy_registry,
            event_sink=event_sink,
            observability=base_observability,
        )

        def echo_node(state: LlmEchoSummaryState) -> LlmEchoSummaryState:
            result = observed_tools.with_observability_context(
                base_observability.with_parent_span(_current_parent(state, context), "echo")
            ).run("echo", text=text)
            echo = {
                "status": _echo_status(result.exit_code),
                "output_summary": result.output_summary,
            }
            return {"current_node": "echo", "echo": echo, "output_payload": {"echo": echo}}

        def llm_node(state: LlmEchoSummaryState) -> LlmEchoSummaryState:
            echo = dict(state.get("echo", {}))
            messages: list[dict[str, Any]] = [
                {"role": "system", "content": "Summarize the user input concisely. Do not expose secrets or raw credentials if present."},
                {"role": "user", "content": text},
            ]
            if echo.get("output_summary"):
                messages.insert(1, {"role": "system", "content": f"EchoTool summary: {echo['output_summary']}"})
            result = observed_llm.with_observability_context(
                base_observability.with_parent_span(_current_parent(state, context), "llm_summary")
            ).complete(messages)
            llm_metadata: dict[str, Any] = {
                "provider": result.provider,
                "model": result.model,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
            }
            output: dict[str, Any] = {
                "summary": result.content,
                "echo": echo,
                "llm": llm_metadata,
            }
            return {"current_node": "llm_summary", "output_payload": output, "llm": llm_metadata}

        graph = StateGraph(LlmEchoSummaryState)
        graph.add_node("echo", _observed_node("echo", echo_node, context))
        graph.add_node("llm_summary", _observed_node("llm_summary", llm_node, context))
        graph.add_edge(START, "echo")
        graph.add_edge("echo", "llm_summary")
        graph.add_edge("llm_summary", END)
        initial: LlmEchoSummaryState = {
            "input_summary": summarize_mapping(dict(input_payload)),
            "output_payload": {},
            "current_node": "workflow",
            "metadata": {},
        }
        final = graph.compile(name="llm_echo_summary").invoke(initial)
        return WorkflowExecutionResult(
            output=dict(final.get("output_payload", {})),
            metadata={"last_step_name": str(final.get("current_node", ""))},
        )


def _observed_node(name, func, context: WorkflowExecutionContext):
    def wrapped(state):
        sink = cast(EventSink | None, context.event_sink)
        if sink is None:
            return func(state)
        span = sink.span_started(
            context.run_id or 0,
            span_type=obs_events.SPAN_NODE,
            name=name,
            node_name=name,
            parent=context.parent_span,
            metadata={"node_name": name},
        )
        state = dict(state)
        state["_node_span"] = span
        try:
            result = func(state)
        except Exception as exc:
            failure_message = str(exc)
            suppress_observability_failure(
                lambda: sink.span_failed(span, error_message=failure_message, metadata={"node_name": name}),
                context={"component": "reference_workflow", "operation": "span_failed", "node_name": name},
            )
            raise
        sink.span_completed(
            span,
            output_summary=json.dumps(summarize_mapping(dict(result)), ensure_ascii=False, sort_keys=True, default=str),
            metrics={"ok": True},
            metadata={"node_name": name},
        )
        return result
    return wrapped


def _current_parent(
    state: Mapping[str, object], context: WorkflowExecutionContext
) -> SpanRef | None:
    return cast(SpanRef | None, state.get("_node_span", context.parent_span))


def _primary_text(payload: Mapping[str, object]) -> str:
    for key in ("text", "prompt", "input", "message"):
        value = payload.get(key)
        if isinstance(value, str):
            return value
    return ""


def _echo_status(exit_code: int) -> str:
    if exit_code == 0:
        return "succeeded"
    if exit_code == POLICY_DENIED_EXIT_CODE:
        return "denied"
    return "failed"
