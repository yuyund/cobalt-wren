from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json

from langgraph_automation.api.errors import WorkflowCheckpointCompatibilityError
from langgraph_automation.api.stores import ArtifactStore, ArtifactWriteRequest, CheckpointStore, CheckpointWriteRequest, StoredArtifact, StoredCheckpoint
from langgraph_automation.api.workflow import WorkflowExecutionContext, WorkflowExecutionResult, WorkflowResumeRequest

_NAMESPACE = "plain-confirmation"
_CHECKPOINT_ID = "awaiting-confirmation-v1"
_STATE_SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class PlainPythonExecutable:
    artifact_store: ArtifactStore
    checkpoint_store: CheckpointStore

    def execute(self, input_payload: Mapping[str, object], *, context: WorkflowExecutionContext) -> WorkflowExecutionResult:
        state = {
            "schema_version": _STATE_SCHEMA_VERSION,
            "phase": "awaiting_confirmation",
            "subject": _required_text(input_payload, "subject"),
            "message": _required_text(input_payload, "message"),
        }
        checkpoint = self.checkpoint_store.save(
            CheckpointWriteRequest(
                run_id=_run_id(context),
                checkpoint_id=_CHECKPOINT_ID,
                body=json.dumps(state, sort_keys=True).encode(),
                serializer_name="json",
                serializer_version=1,
                content_type="application/json",
                checkpoint_namespace=_NAMESPACE,
                metadata={"schema_version": _STATE_SCHEMA_VERSION, "phase": state["phase"]},
            )
        )
        _emit_checkpoint(context, checkpoint)
        return WorkflowExecutionResult(
            status="paused",
            output={
                "status": "awaiting_confirmation",
                "subject": state["subject"],
                "message": state["message"],
                "checkpoint_id": checkpoint.checkpoint_id,
                "allowed_actions": ["confirm", "cancel"],
            },
            metadata={"framework": "none", "state_schema_version": _STATE_SCHEMA_VERSION},
        )

    def resume(self, request: WorkflowResumeRequest, *, context: WorkflowExecutionContext) -> WorkflowExecutionResult:
        stored = (
            self.checkpoint_store.load_checkpoint(
                _run_id(context), request.checkpoint_id, checkpoint_namespace=_NAMESPACE
            )
            if request.checkpoint_id is not None
            else self.checkpoint_store.load_latest(_run_id(context), checkpoint_namespace=_NAMESPACE)
        )
        if stored is None:
            raise LookupError("plain Python workflow checkpoint is unavailable")
        raw_state = json.loads(stored.body.decode())
        if not isinstance(raw_state, dict):
            raise WorkflowCheckpointCompatibilityError()
        state = _migrate_state(raw_state)
        if state.get("phase") != "awaiting_confirmation":
            raise ValueError("plain Python workflow is not resumable from this phase")
        action = str(request.value.get("action", "")).strip().lower()
        if action not in {"confirm", "cancel"}:
            raise ValueError("resume action must be confirm or cancel")
        decision = "confirmed" if action == "confirm" else "cancelled"
        note_key = "note" if action == "confirm" else "reason"
        result = {
            "schema_version": _STATE_SCHEMA_VERSION,
            "subject": state["subject"],
            "message": state["message"],
            "decision": decision,
            note_key: str(request.value.get(note_key, "")).strip(),
        }
        body = json.dumps(result, sort_keys=True).encode()
        artifact = self.artifact_store.put(
            ArtifactWriteRequest(
                run_id=_run_id(context),
                storage_key=f"plain-confirmation/{_run_id(context)}/decision.json",
                body=body,
                name="plain Python decision",
                kind="decision",
                content_type="application/json",
                metadata={"decision": decision, "schema_version": _STATE_SCHEMA_VERSION},
            )
        )
        _emit_artifact(context, artifact)
        checkpoint = self.checkpoint_store.save(
            CheckpointWriteRequest(
                run_id=_run_id(context),
                checkpoint_id=f"final-{decision}-v1",
                parent_checkpoint_id=stored.checkpoint.checkpoint_id,
                body=body,
                serializer_name="json",
                serializer_version=1,
                content_type="application/json",
                checkpoint_namespace=_NAMESPACE,
                metadata={"schema_version": _STATE_SCHEMA_VERSION, "phase": decision},
            )
        )
        _emit_checkpoint(context, checkpoint)
        return WorkflowExecutionResult(
            output={
                "decision": decision,
                "subject": state["subject"],
                "artifact_key": artifact.storage_key,
                "checkpoint_id": checkpoint.checkpoint_id,
            },
            metadata={"framework": "none", "state_schema_version": _STATE_SCHEMA_VERSION},
        )


def _run_id(context: WorkflowExecutionContext) -> int | str:
    return context.run_id if context.run_id is not None else (context.thread_id or "plain-confirmation")


def _required_text(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} is required")
    return value.strip()


def _emit_artifact(context: WorkflowExecutionContext, artifact: StoredArtifact) -> None:
    callback = getattr(context.event_sink, "artifact_created", None)
    if callable(callback) and isinstance(context.run_id, int):
        callback(context.run_id, artifact.storage_key, artifact.name, artifact.kind, metadata=artifact.metadata, content_type=artifact.content_type or "", size=artifact.size)


def _emit_checkpoint(context: WorkflowExecutionContext, checkpoint: StoredCheckpoint) -> None:
    callback = getattr(context.event_sink, "checkpoint_saved", None)
    if callable(callback) and isinstance(context.run_id, int):
        callback(context.run_id, context.thread_id, checkpoint.checkpoint_id, "filesystem", state_summary=str(checkpoint.metadata), checkpoint_namespace=_NAMESPACE)



def _migrate_state(state: dict[str, object]) -> dict[str, object]:
    version = state.get("schema_version", 0)
    if version == _STATE_SCHEMA_VERSION:
        return dict(state)
    if version == 0:
        subject = state.get("title", state.get("subject"))
        message = state.get("body", state.get("message"))
        phase = state.get("phase", "awaiting_confirmation")
        if not isinstance(subject, str) or not isinstance(message, str) or phase != "awaiting_confirmation":
            raise WorkflowCheckpointCompatibilityError("Legacy workflow checkpoint cannot be migrated safely.")
        return {
            "schema_version": _STATE_SCHEMA_VERSION,
            "phase": "awaiting_confirmation",
            "subject": subject,
            "message": message,
        }
    raise WorkflowCheckpointCompatibilityError(
        f"Workflow checkpoint schema version {version!r} is not supported."
    )
