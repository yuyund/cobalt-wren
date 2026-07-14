'''In-memory checkpoint store for early development.'''

from __future__ import annotations

from typing import Any

from .base import CheckpointStore, CheckpointWriteResult
from .summary import format_state_summary


class MemoryCheckpointStore(CheckpointStore):
    def __init__(self) -> None:
        self._store: dict[int, dict[str, Any]] = {}
        self._counter = 0

    def save(
        self,
        run_id: int,
        state: dict[str, Any],
        *,
        thread_id: str = '',
        checkpoint_namespace: str = '',
        backend: str = 'memory',
        node_name: str = '',
    ) -> CheckpointWriteResult:
        self._store[run_id] = dict(state)
        self._counter += 1
        return CheckpointWriteResult(
            checkpoint_id=f'checkpoint-{self._counter}',
            thread_id=thread_id or str(run_id),
            checkpoint_namespace=checkpoint_namespace,
            backend=backend,
            node_name=node_name,
            state_summary=format_state_summary(state),
        )

    def load(self, run_id: int) -> dict[str, Any] | None:
        state = self._store.get(run_id)
        return None if state is None else dict(state)

    def delete(self, run_id: int) -> None:
        self._store.pop(run_id, None)
