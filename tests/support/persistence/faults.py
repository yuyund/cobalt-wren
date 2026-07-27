"""Deterministic fault-injection wrappers for persistence contract tests."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum
from typing import Callable

from cobalt_wren.core.redaction import redact_text
from cobalt_wren.integrations.artifact.base import ArtifactReadResult, ArtifactStore, ArtifactWriteRequest, StoredArtifact
from cobalt_wren.integrations.checkpoint.base import CheckpointReadResult, CheckpointStore, CheckpointWriteRequest, StoredCheckpoint


class FaultTiming(StrEnum):
    BEFORE = 'before'
    AFTER = 'after'


@dataclass(frozen=True, slots=True)
class FaultPlan:
    operation: str
    timing: FaultTiming
    occurrence: int | None
    exception_factory: Callable[[], Exception]

    def matches(self, operation: str, call_count: int) -> bool:
        return self.operation == operation and (self.occurrence is None or self.occurrence == call_count)


@dataclass(frozen=True, slots=True)
class FaultRecord:
    operation: str
    call_count: int
    safe_identifier: str
    timing: FaultTiming
    delegate_ran: bool


class _FaultingBase:
    def __init__(self, *, plan: FaultPlan | None = None) -> None:
        self._plan = plan
        self._call_counts: dict[str, int] = defaultdict(int)
        self.records: list[FaultRecord] = []

    def _record(self, *, operation: str, call_count: int, safe_identifier: str, timing: FaultTiming, delegate_ran: bool) -> None:
        self.records.append(
            FaultRecord(
                operation=operation,
                call_count=call_count,
                safe_identifier=safe_identifier,
                timing=timing,
                delegate_ran=delegate_ran,
            )
        )

    def _should_fault(self, operation: str, call_count: int, timing: FaultTiming) -> bool:
        return self._plan is not None and self._plan.timing == timing and self._plan.matches(operation, call_count)

    @staticmethod
    def _safe_identifier(identifier: str) -> str:
        return redact_text(identifier)


class FaultingArtifactStore(_FaultingBase, ArtifactStore):
    """ArtifactStore wrapper that injects deterministic failures."""

    def __init__(self, inner: ArtifactStore, *, plan: FaultPlan | None = None) -> None:
        super().__init__(plan=plan)
        self._inner = inner

    def put(self, request: ArtifactWriteRequest) -> StoredArtifact:
        operation = 'put'
        call_count = self._call_counts[operation] + 1
        self._call_counts[operation] = call_count
        safe_identifier = self._safe_identifier(request.storage_key)
        if self._should_fault(operation, call_count, FaultTiming.BEFORE):
            self._record(operation=operation, call_count=call_count, safe_identifier=safe_identifier, timing=FaultTiming.BEFORE, delegate_ran=False)
            raise self._plan.exception_factory()  # type: ignore[union-attr]
        result = self._inner.put(request)
        self._record(operation=operation, call_count=call_count, safe_identifier=safe_identifier, timing=FaultTiming.AFTER, delegate_ran=True)
        if self._should_fault(operation, call_count, FaultTiming.AFTER):
            raise self._plan.exception_factory()  # type: ignore[union-attr]
        return result

    def get(self, artifact_id: str) -> ArtifactReadResult | None:
        operation = 'get'
        call_count = self._call_counts[operation] + 1
        self._call_counts[operation] = call_count
        safe_identifier = self._safe_identifier(artifact_id)
        if self._should_fault(operation, call_count, FaultTiming.BEFORE):
            self._record(operation=operation, call_count=call_count, safe_identifier=safe_identifier, timing=FaultTiming.BEFORE, delegate_ran=False)
            raise self._plan.exception_factory()  # type: ignore[union-attr]
        result = self._inner.get(artifact_id)
        self._record(operation=operation, call_count=call_count, safe_identifier=safe_identifier, timing=FaultTiming.AFTER, delegate_ran=True)
        if self._should_fault(operation, call_count, FaultTiming.AFTER):
            raise self._plan.exception_factory()  # type: ignore[union-attr]
        return result

    def list_for_run(self, run_id: int | str) -> list[StoredArtifact]:
        operation = 'list_for_run'
        call_count = self._call_counts[operation] + 1
        self._call_counts[operation] = call_count
        safe_identifier = self._safe_identifier(str(run_id))
        if self._should_fault(operation, call_count, FaultTiming.BEFORE):
            self._record(operation=operation, call_count=call_count, safe_identifier=safe_identifier, timing=FaultTiming.BEFORE, delegate_ran=False)
            raise self._plan.exception_factory()  # type: ignore[union-attr]
        result = self._inner.list_for_run(run_id)
        self._record(operation=operation, call_count=call_count, safe_identifier=safe_identifier, timing=FaultTiming.AFTER, delegate_ran=True)
        if self._should_fault(operation, call_count, FaultTiming.AFTER):
            raise self._plan.exception_factory()  # type: ignore[union-attr]
        return result


class FaultingCheckpointStore(_FaultingBase, CheckpointStore):
    """CheckpointStore wrapper that injects deterministic failures."""

    def __init__(self, inner: CheckpointStore, *, plan: FaultPlan | None = None) -> None:
        super().__init__(plan=plan)
        self._inner = inner

    def save(self, request: CheckpointWriteRequest) -> StoredCheckpoint:
        operation = 'save'
        call_count = self._call_counts[operation] + 1
        self._call_counts[operation] = call_count
        safe_identifier = self._safe_identifier(f'{request.run_id}:{request.checkpoint_namespace}:{request.checkpoint_id}')
        if self._should_fault(operation, call_count, FaultTiming.BEFORE):
            self._record(operation=operation, call_count=call_count, safe_identifier=safe_identifier, timing=FaultTiming.BEFORE, delegate_ran=False)
            raise self._plan.exception_factory()  # type: ignore[union-attr]
        result = self._inner.save(request)
        self._record(operation=operation, call_count=call_count, safe_identifier=safe_identifier, timing=FaultTiming.AFTER, delegate_ran=True)
        if self._should_fault(operation, call_count, FaultTiming.AFTER):
            raise self._plan.exception_factory()  # type: ignore[union-attr]
        return result

    def load_latest(self, run_id: int | str, *, checkpoint_namespace: str = '') -> CheckpointReadResult | None:
        operation = 'load_latest'
        call_count = self._call_counts[operation] + 1
        self._call_counts[operation] = call_count
        safe_identifier = self._safe_identifier(f'{run_id}:{checkpoint_namespace}')
        if self._should_fault(operation, call_count, FaultTiming.BEFORE):
            self._record(operation=operation, call_count=call_count, safe_identifier=safe_identifier, timing=FaultTiming.BEFORE, delegate_ran=False)
            raise self._plan.exception_factory()  # type: ignore[union-attr]
        result = self._inner.load_latest(run_id, checkpoint_namespace=checkpoint_namespace)
        self._record(operation=operation, call_count=call_count, safe_identifier=safe_identifier, timing=FaultTiming.AFTER, delegate_ran=True)
        if self._should_fault(operation, call_count, FaultTiming.AFTER):
            raise self._plan.exception_factory()  # type: ignore[union-attr]
        return result

    def load_checkpoint(self, run_id: int | str, checkpoint_id: str, *, checkpoint_namespace: str = '') -> CheckpointReadResult | None:
        operation = 'load_checkpoint'
        call_count = self._call_counts[operation] + 1
        self._call_counts[operation] = call_count
        safe_identifier = self._safe_identifier(f'{run_id}:{checkpoint_namespace}:{checkpoint_id}')
        if self._should_fault(operation, call_count, FaultTiming.BEFORE):
            self._record(operation=operation, call_count=call_count, safe_identifier=safe_identifier, timing=FaultTiming.BEFORE, delegate_ran=False)
            raise self._plan.exception_factory()  # type: ignore[union-attr]
        result = self._inner.load_checkpoint(run_id, checkpoint_id, checkpoint_namespace=checkpoint_namespace)
        self._record(operation=operation, call_count=call_count, safe_identifier=safe_identifier, timing=FaultTiming.AFTER, delegate_ran=True)
        if self._should_fault(operation, call_count, FaultTiming.AFTER):
            raise self._plan.exception_factory()  # type: ignore[union-attr]
        return result

    def list_for_run(self, run_id: int | str, *, checkpoint_namespace: str = '') -> list[StoredCheckpoint]:
        operation = 'list_for_run'
        call_count = self._call_counts[operation] + 1
        self._call_counts[operation] = call_count
        safe_identifier = self._safe_identifier(f'{run_id}:{checkpoint_namespace}')
        if self._should_fault(operation, call_count, FaultTiming.BEFORE):
            self._record(operation=operation, call_count=call_count, safe_identifier=safe_identifier, timing=FaultTiming.BEFORE, delegate_ran=False)
            raise self._plan.exception_factory()  # type: ignore[union-attr]
        result = self._inner.list_for_run(run_id, checkpoint_namespace=checkpoint_namespace)
        self._record(operation=operation, call_count=call_count, safe_identifier=safe_identifier, timing=FaultTiming.AFTER, delegate_ran=True)
        if self._should_fault(operation, call_count, FaultTiming.AFTER):
            raise self._plan.exception_factory()  # type: ignore[union-attr]
        return result
