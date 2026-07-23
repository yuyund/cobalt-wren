"""Process-local cooperative execution-control registry."""
from __future__ import annotations

from dataclasses import dataclass
from threading import Event, Lock
import time

from langgraph_automation.api.workflow import WorkflowExecutionControl


@dataclass(slots=True)
class _ActiveControl:
    cancelled: Event
    deadline_monotonic: float | None


_lock = Lock()
_active: dict[int, _ActiveControl] = {}


def begin_execution_control(run_id: int, *, timeout_seconds: float | None = None) -> WorkflowExecutionControl:
    deadline = time.monotonic() + timeout_seconds if timeout_seconds is not None else None
    active = _ActiveControl(cancelled=Event(), deadline_monotonic=deadline)
    with _lock:
        _active[run_id] = active
    return WorkflowExecutionControl(cancellation_requested=active.cancelled.is_set, deadline_monotonic=deadline)


def request_cancellation(run_id: int) -> bool:
    with _lock:
        active = _active.get(run_id)
    if active is None:
        return False
    active.cancelled.set()
    return True


def finish_execution_control(run_id: int) -> None:
    with _lock:
        _active.pop(run_id, None)
