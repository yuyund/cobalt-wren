"""Run detail component registry owned by the web renderer."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class RunComponentSpec:
    key: str
    template_name: str
    order: int
    refresh_scope: str = "live"

_RUN_COMPONENTS = (
    RunComponentSpec("run.current_state", "dynamic/components/run_current_state.html", 10),
    RunComponentSpec("run.native_telemetry", "dynamic/components/native_telemetry.html", 12),
    RunComponentSpec("run.failure_diagnostic", "dynamic/components/run_failure_diagnostic.html", 15),
    RunComponentSpec("run.llm_conversation", "dynamic/components/llm_conversation.html", 20),
    RunComponentSpec("run.node_output", "dynamic/components/node_final_output.html", 30),
    RunComponentSpec("run.timeline", "dynamic/components/execution_timeline.html", 40),
)

def get_run_live_components() -> tuple[RunComponentSpec, ...]:
    return tuple(sorted(_RUN_COMPONENTS, key=lambda component: component.order))
