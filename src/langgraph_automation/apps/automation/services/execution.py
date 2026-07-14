"""Execution dispatch for synchronous and future worker-backed runs."""

from __future__ import annotations

from langgraph_automation.apps.automation.models.run import Run
from langgraph_automation.apps.automation.services.runtime import build_graph_runtime
from langgraph_automation.graphs.runner import ExecutionResult, GraphRunner, build_graph_runner
from langgraph_automation.graphs.runtime import GraphRuntime


def dispatch_run_execution(run: Run, *, runtime: GraphRuntime | None = None, runner: GraphRunner | None = None) -> ExecutionResult:
    runtime = runtime or build_graph_runtime(run)
    runner = runner or build_graph_runner()
    return runner.run_graph_once(run_id=run.pk, runtime=runtime, input_payload=run.input_payload)
