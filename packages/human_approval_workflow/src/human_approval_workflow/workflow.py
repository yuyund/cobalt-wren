"""Durable LangGraph human approval workflow."""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
import base64
import json
from typing import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from langgraph_automation.api.stores import ArtifactStore, ArtifactWriteRequest, CheckpointStore, CheckpointWriteRequest
from langgraph_automation.api.workflow import WorkflowExecutionContext, WorkflowExecutionResult, WorkflowResumeRequest

_NAMESPACE = "human-approval"
_PAUSE_CHECKPOINT_ID = "approval-pause"


class ApprovalState(TypedDict, total=False):
    title: str
    proposal: str
    decision: str
    reviewer_note: str
    revision_count: int
    artifact_key: str


@dataclass(frozen=True, slots=True)
class HumanApprovalExecutable:
    artifact_store: ArtifactStore
    checkpoint_store: CheckpointStore

    def execute(self, input_payload: Mapping[str, object], *, context: WorkflowExecutionContext) -> WorkflowExecutionResult:
        saver = InMemorySaver()
        result = self._build_graph(saver, context).invoke({"title": _required_text(input_payload, "title"), "proposal": _required_text(input_payload, "proposal"), "revision_count": 0}, self._config(context))
        return self._normalize(result, saver=saver, context=context)

    def resume(self, request: WorkflowResumeRequest, *, context: WorkflowExecutionContext) -> WorkflowExecutionResult:
        stored = (
            self.checkpoint_store.load_checkpoint(
                _run_id(context), request.checkpoint_id, checkpoint_namespace=_NAMESPACE
            )
            if request.checkpoint_id is not None
            else self.checkpoint_store.load_latest(
                _run_id(context), checkpoint_namespace=_NAMESPACE
            )
        )
        if stored is None:
            raise LookupError("paused workflow checkpoint is unavailable")
        saver = _restore_saver(stored.body)
        result = self._build_graph(saver, context).invoke(Command(resume=dict(request.value)), self._config(context))
        return self._normalize(result, saver=saver, context=context)

    def _build_graph(self, saver: InMemorySaver, context: WorkflowExecutionContext):
        def approval(state: ApprovalState) -> ApprovalState:
            response = interrupt({"kind": "approval_request", "title": state["title"], "proposal": state["proposal"], "revision_count": state.get("revision_count", 0), "allowed_decisions": ["approve", "reject", "revise"]})
            if not isinstance(response, Mapping):
                raise ValueError("approval response must be a mapping")
            decision = str(response.get("decision", "")).strip().lower()
            if decision not in {"approve", "reject", "revise"}:
                raise ValueError("approval decision must be approve, reject, or revise")
            update: ApprovalState = {"decision": decision, "reviewer_note": str(response.get("note", "")).strip()}
            revised = response.get("proposal")
            if decision == "revise" and isinstance(revised, str) and revised.strip():
                update["proposal"] = revised.strip()
            return update

        def revise(state: ApprovalState) -> ApprovalState:
            return {"decision": "", "revision_count": state.get("revision_count", 0) + 1}

        def finalize(state: ApprovalState) -> ApprovalState:
            run_id = _run_id(context)
            decision = "approved" if state["decision"] == "approve" else "rejected"
            body = json.dumps({"title": state["title"], "proposal": state["proposal"], "decision": decision, "reviewer_note": state.get("reviewer_note", ""), "revision_count": state.get("revision_count", 0)}, ensure_ascii=False, sort_keys=True).encode()
            stored = self.artifact_store.put(ArtifactWriteRequest(run_id=run_id, storage_key=f"human-approval/{run_id}/decision.json", body=body, name="approval decision", kind="approval", content_type="application/json", metadata={"decision": decision}))
            return {"decision": decision, "artifact_key": stored.storage_key}

        graph = StateGraph(ApprovalState)
        graph.add_node("approval", approval)
        graph.add_node("revise", revise)
        graph.add_node("finalize", finalize)
        graph.add_edge(START, "approval")
        graph.add_conditional_edges("approval", lambda state: state["decision"], {"approve": "finalize", "reject": "finalize", "revise": "revise"})
        graph.add_edge("revise", "approval")
        graph.add_edge("finalize", END)
        return graph.compile(checkpointer=saver, name="human_approval")

    def _normalize(self, result: Mapping[str, object], *, saver: InMemorySaver, context: WorkflowExecutionContext) -> WorkflowExecutionResult:
        interrupts = result.get("__interrupt__")
        if interrupts:
            request_value = _interrupt_value(interrupts)
            revision_count = (
                int(request_value.get("revision_count", 0))
                if isinstance(request_value, Mapping)
                else 0
            )
            previous = self.checkpoint_store.load_latest(
                _run_id(context), checkpoint_namespace=_NAMESPACE
            )
            checkpoint = self.checkpoint_store.save(
                CheckpointWriteRequest(
                    run_id=_run_id(context),
                    checkpoint_id=f"{_PAUSE_CHECKPOINT_ID}-{revision_count}",
                    parent_checkpoint_id=(
                        previous.checkpoint.checkpoint_id if previous is not None else None
                    ),
                    body=_snapshot_saver(saver),
                    serializer_name="json-base64",
                    serializer_version=1,
                    content_type="application/json",
                    checkpoint_namespace=_NAMESPACE,
                    metadata={
                        "status": "paused",
                        "workflow": "human.approval",
                        "revision_count": revision_count,
                    },
                )
            )
            return WorkflowExecutionResult(status="paused", output={"approval_request": request_value, "checkpoint_id": checkpoint.checkpoint_id}, metadata={"pause_reason": "human_approval"})
        return WorkflowExecutionResult(output={"decision": result.get("decision", ""), "proposal": result.get("proposal", ""), "reviewer_note": result.get("reviewer_note", ""), "revision_count": result.get("revision_count", 0), "artifact_key": result.get("artifact_key", "")}, metadata={"resumed": True})

    @staticmethod
    def _config(context: WorkflowExecutionContext) -> dict[str, object]:
        return {"configurable": {"thread_id": context.thread_id or str(_run_id(context))}}


def _run_id(context: WorkflowExecutionContext) -> int | str:
    return context.run_id if context.run_id is not None else (context.thread_id or "human-approval")


def _required_text(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} is required")
    return value.strip()


def _interrupt_value(interrupts: object) -> object:
    if isinstance(interrupts, (list, tuple)) and interrupts:
        return getattr(interrupts[0], "value", interrupts[0])
    return interrupts


def _typed(value: tuple[str, bytes]) -> list[str]:
    return [value[0], base64.b64encode(value[1]).decode("ascii")]


def _untyped(value: list[str]) -> tuple[str, bytes]:
    return value[0], base64.b64decode(value[1])


def _snapshot_saver(saver: InMemorySaver) -> bytes:
    storage = [[thread, namespace, checkpoint_id, _typed(checkpoint), _typed(metadata), parent] for thread, namespaces in saver.storage.items() for namespace, checkpoints in namespaces.items() for checkpoint_id, (checkpoint, metadata, parent) in checkpoints.items()]
    writes = [[thread, namespace, checkpoint_id, task_id, index, stored_task_id, channel, _typed(value), task_path] for (thread, namespace, checkpoint_id), items in saver.writes.items() for (task_id, index), (stored_task_id, channel, value, task_path) in items.items()]
    blobs = [[thread, namespace, channel, version, _typed(value)] for (thread, namespace, channel, version), value in saver.blobs.items()]
    return json.dumps({"storage": storage, "writes": writes, "blobs": blobs}, separators=(",", ":")).encode()


def _restore_saver(body: bytes) -> InMemorySaver:
    payload = json.loads(body.decode())
    saver = InMemorySaver()
    saver.storage = defaultdict(lambda: defaultdict(dict))
    for thread, namespace, checkpoint_id, checkpoint, metadata, parent in payload["storage"]:
        saver.storage[thread][namespace][checkpoint_id] = (_untyped(checkpoint), _untyped(metadata), parent)
    saver.writes = defaultdict(dict)
    for thread, namespace, checkpoint_id, task_id, index, stored_task_id, channel, value, task_path in payload["writes"]:
        saver.writes[(thread, namespace, checkpoint_id)][(task_id, index)] = (stored_task_id, channel, _untyped(value), task_path)
    saver.blobs = {(thread, namespace, channel, version): _untyped(value) for thread, namespace, channel, version, value in payload["blobs"]}
    return saver
