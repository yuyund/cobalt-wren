# Checkpoint Store Protocol Sufficiency Audit

This audit determines whether the current `CheckpointStore` protocol can express versioned durable execution state for future restart and resume work.

Code is the source of truth.
Tests are the source of truth.
Docs record the current decision and the target boundary.

## Current Protocol Surface

The current public store facade re-exports the checkpoint protocol from `src/langgraph_automation/api/stores.py`.

The current protocol surface is:

- `CheckpointStore.save(run_id, state, *, thread_id='', checkpoint_namespace='', backend='', node_name='') -> CheckpointWriteResult`
- `CheckpointStore.load(run_id) -> dict[str, Any] | None`
- `CheckpointStore.delete(run_id) -> None`

The current normalized write result is `CheckpointWriteResult` with fields:

- `checkpoint_id`
- `thread_id`
- `checkpoint_namespace`
- `backend`
- `node_name`
- `state_summary`

There are no versioned checkpoint descriptor, read-result, serializer, size, digest, or lineage fields in the current protocol surface.

## Current Call Sites

Current code-first evidence shows:

- `src/langgraph_automation/apps/automation/services/runtime.py` constructs `MemoryCheckpointStore`
- `src/langgraph_automation/runtime/assembly.py` threads the checkpoint store through `RuntimeDependencies`
- `src/langgraph_automation/graphs/runtime.py` carries the checkpoint store on `GraphRuntime`
- `src/langgraph_automation/integrations/observability/django_event_sink.py` persists `CheckpointMetadata` rows only
- `src/langgraph_automation/apps/automation/services/execution.py` does not write checkpoint bodies
- `src/langgraph_automation/apps/automation/services/runs.py` does not write checkpoint bodies
- `src/langgraph_automation/graphs/runner.py` does not call the checkpoint store

No current production execution path in `src/` calls `CheckpointStore.save`, `load`, or `delete` from the graph execution path.

## Current Behavior Characterization

The current memory backend behaves as a destructive latest snapshot store:

- `save(run_id, state)` replaces the previously stored state for that `run_id`
- `load(run_id)` returns the latest state or `None`
- `delete(run_id)` removes the latest state for that `run_id`
- there is no history listing
- there is no specific-version read
- there is no parent / lineage tracking
- there is no deterministic latest ordering contract beyond overwrite order

That behavior is useful as a characterization of the current memory backend, but it is not sufficient for a versioned durable checkpoint contract.

## Identity / Lineage Mapping

Current code exposes only a partial execution identity:

Framework concept | Current code concept | Current mapping | Problem
--- | --- | --- | ---
`run_id` | store key | `run_id` is the only lookup key | cannot identify multiple versions within the same run
`thread_id` | metadata only | passed through to the write result and event metadata | not part of checkpoint identity
`checkpoint_namespace` | metadata only | passed through to the write result and event metadata | not part of checkpoint identity or lookup
`checkpoint_id` | generated label | `MemoryCheckpointStore` fabricates `checkpoint-N` in memory only | not a durable identity or ordering contract
`parent_checkpoint_id` | absent | no mapping | lineage cannot be represented

Current `CheckpointMetadata` rows store `run`, `thread_id`, `checkpoint_id`, `checkpoint_namespace`, `backend`, `node_name`, `state_summary`, and timestamps, but they do not store checkpoint body, version ordering, serializer identity, or lineage.

## Protocol Sufficiency Matrix

Capability | Current protocol | Code-first evidence | Impact of missing capability | Decision
--- | --- | --- | --- | ---
Actual state body input | PARTIALLY_SUPPORTED | `save(..., state: dict[str, Any])` | state is a Python object, not a versioned body contract | insufficient
Actual state body output | PARTIALLY_SUPPORTED | `load(run_id) -> dict[str, Any] | None` | no descriptor/body split | insufficient
Stable checkpoint identity | NOT_SUPPORTED | `run_id` lookup only | cannot address multiple versions for one execution | insufficient
Run association | PARTIALLY_SUPPORTED | `run_id` exists | one key is not enough for versioned execution state | insufficient
Thread identity | PARTIALLY_SUPPORTED | `thread_id` is metadata only | not part of the lookup or ordering contract | insufficient
Namespace | PARTIALLY_SUPPORTED | `checkpoint_namespace` is metadata only | not part of identity or history semantics | insufficient
Parent / lineage | NOT_SUPPORTED | no parent field | cannot express branching or resume ancestry | insufficient
Version / revision ordering | NOT_SUPPORTED | no revision field | latest selection is not contractual | insufficient
Deterministic latest selection | NOT_SUPPORTED | overwrite order only | restart and concurrency semantics are undefined | insufficient
Specific-version read | NOT_SUPPORTED | no versioned read API | cannot inspect or resume older checkpoint versions | insufficient
History listing | NOT_SUPPORTED | no list API | cannot audit or traverse versions | insufficient
Serializer identity | NOT_SUPPORTED | no serializer field | restart compatibility cannot be expressed | insufficient
Serializer version | NOT_SUPPORTED | no serializer version field | compatibility upgrades cannot be represented | insufficient
Size / digest | NOT_SUPPORTED | no size / digest field | integrity cannot be verified mechanically | insufficient
Safe metadata | PARTIALLY_SUPPORTED | `state_summary` is bounded and redacted | metadata exists but is not a durable version descriptor | insufficient
Immutable version write | NOT_SUPPORTED | current store overwrites by `run_id` | destructive replacement loses prior state | insufficient
Idempotent retry | NOT_SUPPORTED | no canonical write contract | retry safety is undefined | insufficient
Conflict detection | NOT_SUPPORTED | overwrite is silent | concurrent writers can clobber each other | insufficient
Concurrent append | NOT_SUPPORTED | no append / branch semantics | lost updates are not detectable | insufficient
Lost-update detection | NOT_SUPPORTED | no expected-parent or CAS contract | simultaneous writers can silently lose history | insufficient
Restart durability | NOT_SUPPORTED | memory store is process-local only | restart destroys checkpoint state | insufficient
Safe deletion scope | PARTIALLY_SUPPORTED | `delete(run_id)` exists | destructive latest-only semantics only | insufficient for versioned history

## Protocol Sufficiency Decision

Decision: `BLOCKED_BY_PROTOCOL`

Reason:

- the current protocol only expresses a destructive latest snapshot keyed by `run_id`
- versioned checkpoint identity is not expressible
- parent / lineage / history are not expressible
- specific-version read is not expressible
- serializer identity and version are not expressible
- idempotent retry and conflict detection for immutable checkpoint versions are not expressible
- lost-update detection is not expressible

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

Option D, an internal repository plus LangGraph adapter, remains a good later integration layer for resume semantics, but it does not remove the need for a richer checkpoint storage protocol.

## Deferred Work

- FilesystemCheckpointStore implementation is deferred
- checkpoint runtime selection is deferred
- true resume is deferred
- pending writes / interrupts / task replay are deferred
- body / metadata orchestration is deferred

