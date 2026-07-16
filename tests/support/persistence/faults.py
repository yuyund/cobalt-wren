"""Deterministic fault-injection wrappers for persistence contract tests."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Callable

from langgraph_automation.core.redaction import redact_text
from langgraph_automation.integrations.artifact.base import ArtifactStore, ArtifactWriteResult
from langgraph_automation.integrations.checkpoint.base import CheckpointStore, CheckpointWriteResult


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

    def put(self, artifact: ArtifactWriteResult) -> ArtifactWriteResult:
        operation = 'put'
        call_count = self._call_counts[operation] + 1
        self._call_counts[operation] = call_count
        safe_identifier = self._safe_identifier(artifact.storage_key)
        if self._should_fault(operation, call_count, FaultTiming.BEFORE):
            self._record(operation=operation, call_count=call_count, safe_identifier=safe_identifier, timing=FaultTiming.BEFORE, delegate_ran=False)
            raise self._plan.exception_factory()  # type: ignore[union-attr]
        result = self._inner.put(artifact)
        self._record(operation=operation, call_count=call_count, safe_identifier=safe_identifier, timing=FaultTiming.AFTER, delegate_ran=True)
        if self._should_fault(operation, call_count, FaultTiming.AFTER):
            raise self._plan.exception_factory()  # type: ignore[union-attr]
        return result

    def get(self, artifact_id: str) -> ArtifactWriteResult | None:
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

    def list_for_run(self, run_id: int) -> list[ArtifactWriteResult]:
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

    def save(
        self,
        run_id: int,
        state: dict[str, Any],
        *,
        thread_id: str = '',
        checkpoint_namespace: str = '',
        backend: str = '',
        node_name: str = '',
    ) -> CheckpointWriteResult:
        operation = 'save'
        call_count = self._call_counts[operation] + 1
        self._call_counts[operation] = call_count
        safe_identifier = self._safe_identifier(str(run_id))
        if self._should_fault(operation, call_count, FaultTiming.BEFORE):
            self._record(operation=operation, call_count=call_count, safe_identifier=safe_identifier, timing=FaultTiming.BEFORE, delegate_ran=False)
            raise self._plan.exception_factory()  # type: ignore[union-attr]
        result = self._inner.save(
            run_id,
            state,
            thread_id=thread_id,
            checkpoint_namespace=checkpoint_namespace,
            backend=backend,
            node_name=node_name,
        )
        self._record(operation=operation, call_count=call_count, safe_identifier=safe_identifier, timing=FaultTiming.AFTER, delegate_ran=True)
        if self._should_fault(operation, call_count, FaultTiming.AFTER):
            raise self._plan.exception_factory()  # type: ignore[union-attr]
        return result

    def load(self, run_id: int) -> dict[str, Any] | None:
        operation = 'load'
        call_count = self._call_counts[operation] + 1
        self._call_counts[operation] = call_count
        safe_identifier = self._safe_identifier(str(run_id))
        if self._should_fault(operation, call_count, FaultTiming.BEFORE):
            self._record(operation=operation, call_count=call_count, safe_identifier=safe_identifier, timing=FaultTiming.BEFORE, delegate_ran=False)
            raise self._plan.exception_factory()  # type: ignore[union-attr]
        result = self._inner.load(run_id)
        self._record(operation=operation, call_count=call_count, safe_identifier=safe_identifier, timing=FaultTiming.AFTER, delegate_ran=True)
        if self._should_fault(operation, call_count, FaultTiming.AFTER):
            raise self._plan.exception_factory()  # type: ignore[union-attr]
        return result

    def delete(self, run_id: int) -> None:
        operation = 'delete'
        call_count = self._call_counts[operation] + 1
        self._call_counts[operation] = call_count
        safe_identifier = self._safe_identifier(str(run_id))
        if self._should_fault(operation, call_count, FaultTiming.BEFORE):
            self._record(operation=operation, call_count=call_count, safe_identifier=safe_identifier, timing=FaultTiming.BEFORE, delegate_ran=False)
            raise self._plan.exception_factory()  # type: ignore[union-attr]
        result = self._inner.delete(run_id)
        self._record(operation=operation, call_count=call_count, safe_identifier=safe_identifier, timing=FaultTiming.AFTER, delegate_ran=True)
        if self._should_fault(operation, call_count, FaultTiming.AFTER):
            raise self._plan.exception_factory()  # type: ignore[union-attr]
        return result
