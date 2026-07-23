> **Historical snapshot:** This audit records an earlier GraphRuntime-based architecture. The production graph package and control-plane graph path have been removed. Current behavior is defined by `docs/architecture/design/EXECUTION_LIFECYCLE_CONVERGENCE.md`.

# Checkpoint Store Protocol Sufficiency Audit

This audit determines whether the current `CheckpointStore` protocol can express versioned durable execution state for future restart and resume work.

The checkpoint store contract is now versioned, linear, serializer-aware, idempotent, and conflict-aware.
It is a request / descriptor / read-result separation rather than a destructive latest snapshot contract.
The filesystem checkpoint backend is now implemented, and checkpoint runtime selection is typed at startup while concrete store construction remains runtime-assembly scoped.

Code is the source of truth.
Tests are the source of truth.
Docs record the current decision and the target boundary.

## Current Protocol Surface

The current public store facade re-exports the checkpoint protocol from `src/langgraph_automation/api/stores.py`.

The current protocol surface is:

- `CheckpointStore.save(request: CheckpointWriteRequest) -> StoredCheckpoint`
- `CheckpointStore.load_latest(run_id: int | str, *, checkpoint_namespace='') -> CheckpointReadResult | None`
- `CheckpointStore.load_checkpoint(run_id: int | str, checkpoint_id: str, *, checkpoint_namespace='') -> CheckpointReadResult | None`
- `CheckpointStore.list_for_run(run_id: int | str, *, checkpoint_namespace='') -> list[StoredCheckpoint]`

The current request / descriptor / read-result types are:

- `CheckpointWriteRequest`
- `StoredCheckpoint`
- `CheckpointReadResult`

The current descriptor fields include:

- `run_id`
- `checkpoint_namespace`
- `checkpoint_id`
- `parent_checkpoint_id`
- `revision`
- `serializer_name`
- `serializer_version`
- `content_type`
- `size`
- `digest`
- `metadata`

The current protocol does not expose destructive delete, latest-state replacement, or any hidden versioned side channel.

## Current Call Sites

Current code-first evidence shows:

- `src/langgraph_automation/apps/automation/services/runtime.py` binds normalized deployment configuration and delegates checkpoint store construction to runtime assembly
- `src/langgraph_automation/runtime/assembly.py` threads the checkpoint store through `RuntimeDependencies`
- `src/langgraph_automation/graphs/runtime.py` carries the checkpoint store on `GraphRuntime`
- `src/langgraph_automation/integrations/checkpoint/filesystem_store.py` implements the durable filesystem backend
- `src/langgraph_automation/integrations/observability/django_event_sink.py` persists `CheckpointMetadata` rows only
- `src/langgraph_automation/apps/automation/services/execution.py` does not write checkpoint bodies
- `src/langgraph_automation/apps/automation/services/runs.py` does not write checkpoint bodies
- `src/langgraph_automation/graphs/runner.py` does not call the checkpoint store

No current production execution path in `src/` calls checkpoint persistence from the graph execution path.

## Current Behavior Characterization

The current memory backend now behaves as a linear append-only versioned checkpoint store:

- `save(request)` appends immutable versions
- `load_latest(run_id, namespace)` returns the current head
- `load_checkpoint(run_id, checkpoint_id, namespace)` returns a specific version
- `list_for_run(run_id, namespace)` returns descriptors ordered by revision
- same identity / same canonical request is idempotent
- same identity / different canonical request is a conflict
- stale-parent writes are conflicts
- there is no destructive overwrite contract
- there is no versioned delete contract
- there is no history shortcut that bypasses revision ordering

That behavior is the reference checkpoint contract for future durable backends.

## Identity / Lineage Mapping

Current code exposes the execution stream and checkpoint identity explicitly:

Framework concept | Current code concept | Current mapping | Problem
--- | --- | --- | ---
`run_id` | stream identity | part of the execution stream key | none
`checkpoint_namespace` | stream identity | part of the execution stream key | none
`checkpoint_id` | checkpoint identity | caller-issued immutable version ID | none
`parent_checkpoint_id` | lineage + expected head | persisted lineage and head precondition | none
`revision` | ordering | store-assigned linear order | none

Current `CheckpointMetadata` rows still store metadata only. They do not store checkpoint bodies.

## Protocol Sufficiency Matrix

Capability | Current protocol | Code-first evidence | Impact of missing capability | Decision
--- | --- | --- | --- | ---
Actual state body input | SUPPORTED | `save(request.body: bytes)` | none | supported
Actual state body output | SUPPORTED | `load_latest()` / `load_checkpoint()` return `CheckpointReadResult` | none | supported
Stable checkpoint identity | SUPPORTED | `run_id + checkpoint_namespace + checkpoint_id` | none | supported
Run association | SUPPORTED | `run_id` exists | none | supported
Namespace | SUPPORTED | `checkpoint_namespace` is part of identity | none | supported
Parent / lineage | SUPPORTED | `parent_checkpoint_id` is stored and validated | none | supported
Version / revision ordering | SUPPORTED | `revision` is store-assigned | none | supported
Deterministic latest selection | SUPPORTED | `load_latest()` resolves the current head | none | supported
Specific-version read | SUPPORTED | `load_checkpoint()` exists | none | supported
History listing | SUPPORTED | `list_for_run()` returns revision-ordered descriptors | none | supported
Serializer identity | SUPPORTED | `serializer_name` is persisted | none | supported
Serializer version | SUPPORTED | `serializer_version` is persisted | none | supported
Size / digest | SUPPORTED | `size` and `digest` are stored | none | supported
Safe metadata | SUPPORTED | metadata is preserved as a lossless logical JSON value and defensively isolated | none | supported
Immutable version write | SUPPORTED | same identity does not overwrite prior versions | none | supported
Idempotent retry | SUPPORTED | same canonical request returns the existing descriptor | none | supported
Conflict detection | SUPPORTED | changed immutable identity or stale parent conflicts | none | supported
Concurrent append | SUPPORTED | linear parent/head precondition supports same-parent conflict detection | none | supported
Lost-update detection | SUPPORTED | stale-parent conflict is observable | none | supported
Restart durability | NOT_SUPPORTED | `MemoryCheckpointStore` remains EPHEMERAL | checkpoint bodies are not process-restart durable | backend required
Safe deletion scope | NOT_SUPPORTED | delete is removed from the versioned protocol | delete / prune / retention remain deferred | intentional

## Protocol Sufficiency Decision

Decision: `APPROVED_FOR_IMPLEMENTATION`

Reason:

- the current protocol now expresses versioned checkpoint identity
- parent / lineage / revision ordering are explicit
- serializer identity and version are explicit
- specific-version reads and history listing are explicit
- idempotent retry and conflict detection are executable
- the protocol separates request / descriptor / read-result responsibilities

## Target Design Direction

Recommended protocol evolution: Option B

Option B means:

- request / descriptor / read result separation
- explicit versioned read operations
- explicit history listing
- explicit parent / lineage fields
- explicit serializer identity/version fields

Reason:

- it keeps storage semantics separate from LangGraph execution semantics
- it makes immutable, versioned checkpoint records explicit
- it gives a durable filesystem backend a stable target contract

Option D, an internal repository plus LangGraph adapter, remains a good later integration layer for resume semantics, but it does not replace the storage contract.

## Deferred Work

- checkpoint runtime selection is typed and canonical
- true resume is deferred
- pending writes / interrupts / task replay are deferred
- body / metadata orchestration is deferred
