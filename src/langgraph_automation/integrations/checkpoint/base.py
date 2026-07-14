'''Checkpoint store interfaces and normalized write results.'''

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(slots=True, frozen=True)
class CheckpointWriteResult:
    '''Normalized checkpoint metadata returned from checkpoint stores.'''

    checkpoint_id: str
    thread_id: str
    checkpoint_namespace: str
    backend: str
    node_name: str
    state_summary: str = ''


@runtime_checkable
class CheckpointStore(Protocol):
    def save(
        self,
        run_id: int,
        state: dict[str, Any],
        *,
        thread_id: str = '',
        checkpoint_namespace: str = '',
        backend: str = '',
        node_name: str = '',
    ) -> CheckpointWriteResult: ...
    def load(self, run_id: int) -> dict[str, Any] | None: ...
    def delete(self, run_id: int) -> None: ...
