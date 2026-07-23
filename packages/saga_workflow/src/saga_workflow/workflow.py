from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
import operator
from typing import Annotated, TypedDict, cast

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from langgraph_automation.api.stores import ArtifactStore, ArtifactWriteRequest, CheckpointStore, CheckpointWriteRequest, StoredArtifact, StoredCheckpoint
from langgraph_automation.api.workflow import WorkflowExecutionContext, WorkflowExecutionResult, WorkflowResumeRequest

_NAMESPACE = "saga-order-fulfillment"
_OPERATIONS = ("reserve_inventory", "charge_payment", "provision_access")
_COMPENSATIONS = {
    "reserve_inventory": "release_inventory",
    "charge_payment": "refund_payment",
    "provision_access": "revoke_access",
}


class BranchResult(TypedDict):
    operation: str
    status: str
    retryable: bool
    attempt: int
    idempotency_key: str
    detail: str


class SagaState(TypedDict, total=False):
    order_id: str
    operation: str
    failure_plan: dict[str, str]
    attempts: dict[str, int]
    selected_operations: list[str]
    branch_results: Annotated[list[BranchResult], operator.add]


@dataclass(frozen=True, slots=True)
class SagaExecutable:
    artifact_store: ArtifactStore
    checkpoint_store: CheckpointStore

    def execute(self, input_payload: Mapping[str, object], *, context: WorkflowExecutionContext) -> WorkflowExecutionResult:
        order_id = _required_text(input_payload, "order_id")
        failure_plan = _failure_plan(input_payload.get("failure_plan"))
        result = self._graph().invoke({
            "order_id": order_id,
            "failure_plan": failure_plan,
            "attempts": {},
            "selected_operations": list(_OPERATIONS),
            "branch_results": [],
        })
        return self._reconcile(result, context=context)

    def resume(self, request: WorkflowResumeRequest, *, context: WorkflowExecutionContext) -> WorkflowExecutionResult:
        stored = self.checkpoint_store.load_latest(_run_id(context), checkpoint_namespace=_NAMESPACE)
        if stored is None:
            raise LookupError("saga checkpoint is unavailable")
        state = json.loads(stored.body.decode())
        action = str(request.value.get("action", "")).strip().lower()
        if action == "retry_failed":
            failures = [item["operation"] for item in state["branch_results"] if item["status"] == "failed" and item["retryable"]]
            state["selected_operations"] = failures
            state["branch_results"] = [item for item in state["branch_results"] if item["operation"] not in failures]
            for operation in failures:
                state["failure_plan"].pop(operation, None)
            result = self._graph().invoke(state)
            return self._reconcile(result, context=context, parent_checkpoint_id=stored.checkpoint.checkpoint_id)
        if action == "compensate":
            return self._compensate(state, context=context, parent_checkpoint_id=stored.checkpoint.checkpoint_id)
        raise ValueError("saga resume action must be retry_failed or compensate")

    @staticmethod
    def _graph():
        def fan_out(state: SagaState):
            return [Send("execute_branch", {"order_id": state["order_id"], "operation": operation, "failure_plan": state["failure_plan"], "attempts": state["attempts"]}) for operation in state["selected_operations"]]

        def execute_branch(state: SagaState) -> SagaState:
            operation = str(state["operation"])
            attempts = dict(state.get("attempts", {}))
            attempt = attempts.get(operation, 0) + 1
            planned = state.get("failure_plan", {}).get(operation, "")
            failed = planned in {"retryable", "fatal"}
            result: BranchResult = {
                "operation": operation,
                "status": "failed" if failed else "succeeded",
                "retryable": planned == "retryable",
                "attempt": attempt,
                "idempotency_key": f"{state['order_id']}:{operation}",
                "detail": planned or "completed",
            }
            return {"branch_results": [result]}

        graph = StateGraph(SagaState)
        graph.add_node("execute_branch", execute_branch)
        graph.add_conditional_edges(START, fan_out, ["execute_branch"])
        graph.add_edge("execute_branch", END)
        return graph.compile(name="order_fulfillment_saga")

    def _reconcile(self, state: Mapping[str, object], *, context: WorkflowExecutionContext, parent_checkpoint_id: str | None = None) -> WorkflowExecutionResult:
        raw_results = cast(list[Mapping[str, object]], state.get("branch_results", []))
        results = [dict(item) for item in raw_results]
        retryable = [item for item in results if item["status"] == "failed" and item["retryable"]]
        fatal = [item for item in results if item["status"] == "failed" and not item["retryable"]]
        if retryable or fatal:
            checkpoint_id = f"partial-{sum(int(str(item['attempt'])) for item in results)}"
            checkpoint = self.checkpoint_store.save(CheckpointWriteRequest(
                run_id=_run_id(context),
                checkpoint_id=checkpoint_id,
                parent_checkpoint_id=parent_checkpoint_id,
                body=json.dumps({
                    "order_id": state["order_id"],
                    "failure_plan": state.get("failure_plan", {}),
                    "attempts": {item["operation"]: item["attempt"] for item in results},
                    "selected_operations": [],
                    "branch_results": results,
                }, sort_keys=True).encode(),
                serializer_name="json",
                serializer_version=1,
                content_type="application/json",
                checkpoint_namespace=_NAMESPACE,
                metadata={"status": "partial_failure", "retryable_count": len(retryable), "fatal_count": len(fatal)},
            ))
            allowed = (["retry_failed"] if retryable else []) + ["compensate"]
            _emit_checkpoint(context, checkpoint, checkpoint_namespace=_NAMESPACE)
            return WorkflowExecutionResult(
                status="paused",
                output={"status": "partial_failure", "results": results, "checkpoint_id": checkpoint.checkpoint_id, "allowed_actions": allowed},
                metadata={"partial_failure": True},
            )
        return self._finalize(state, context=context, status="completed", compensations=[], parent_checkpoint_id=parent_checkpoint_id)

    def _compensate(self, state: Mapping[str, object], *, context: WorkflowExecutionContext, parent_checkpoint_id: str) -> WorkflowExecutionResult:
        raw_results = cast(list[dict[str, object]], state["branch_results"])
        succeeded = [item for item in raw_results if item["status"] == "succeeded"]
        compensations: list[dict[str, object]] = []
        for item in reversed(succeeded):
            operation = str(item["operation"])
            compensation = _COMPENSATIONS[operation]
            compensations.append({
                "operation": compensation,
                "status": "succeeded",
                "idempotency_key": f"{state['order_id']}:{compensation}",
                "compensates": operation,
            })
        return self._finalize(state, context=context, status="compensated", compensations=compensations, parent_checkpoint_id=parent_checkpoint_id)

    def _finalize(self, state: Mapping[str, object], *, context: WorkflowExecutionContext, status: str, compensations: list[dict[str, object]], parent_checkpoint_id: str | None = None) -> WorkflowExecutionResult:
        payload = {"order_id": state["order_id"], "status": status, "results": state["branch_results"], "compensations": compensations}
        body = json.dumps(payload, sort_keys=True).encode()
        run_id = _run_id(context)
        artifact = self.artifact_store.put(ArtifactWriteRequest(run_id=run_id, storage_key=f"saga/{run_id}/reconciliation.json", body=body, name="saga reconciliation", kind="reconciliation", content_type="application/json", metadata={"status": status}))
        _emit_artifact(context, artifact)
        checkpoint = self.checkpoint_store.save(CheckpointWriteRequest(run_id=run_id, checkpoint_id=f"final-{status}", parent_checkpoint_id=parent_checkpoint_id, body=body, serializer_name="json", serializer_version=1, content_type="application/json", checkpoint_namespace=_NAMESPACE, metadata={"status": status}))
        _emit_checkpoint(context, checkpoint, checkpoint_namespace=_NAMESPACE)
        return WorkflowExecutionResult(output={**payload, "artifact_key": artifact.storage_key, "checkpoint_id": checkpoint.checkpoint_id})


def _run_id(context: WorkflowExecutionContext) -> int | str:
    return context.run_id if context.run_id is not None else (context.thread_id or "saga")


def _required_text(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} is required")
    return value.strip()


def _failure_plan(value: object) -> dict[str, str]:
    if not isinstance(value, Mapping):
        return {}
    plan = {str(key): str(item) for key, item in value.items()}
    invalid = {key: item for key, item in plan.items() if key not in _OPERATIONS or item not in {"retryable", "fatal"}}
    if invalid:
        raise ValueError("failure_plan contains unsupported operation or failure type")
    return plan


def _emit_artifact(context: WorkflowExecutionContext, artifact: StoredArtifact) -> None:
    callback = getattr(context.event_sink, "artifact_created", None)
    if callable(callback) and isinstance(context.run_id, int):
        callback(context.run_id, artifact.storage_key, artifact.name, artifact.kind, metadata=artifact.metadata, content_type=artifact.content_type, size=artifact.size)


def _emit_checkpoint(context: WorkflowExecutionContext, checkpoint: StoredCheckpoint, *, checkpoint_namespace: str) -> None:
    callback = getattr(context.event_sink, "checkpoint_saved", None)
    if callable(callback) and isinstance(context.run_id, int):
        callback(context.run_id, context.thread_id, checkpoint.checkpoint_id, "filesystem", state_summary=str(checkpoint.metadata), checkpoint_namespace=checkpoint_namespace)
