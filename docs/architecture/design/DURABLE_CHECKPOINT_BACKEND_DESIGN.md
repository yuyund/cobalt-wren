# Durable Checkpoint Backend Design

This document describes the target design for a future durable checkpoint backend.

Status: blocked by protocol.

The current `CheckpointStore` protocol cannot yet express immutable checkpoint versions, lineage, serializer compatibility, specific-version reads, or history listing. This design remains provisional until the protocol is evolved.

## Purpose

- preserve versioned execution state for restart and audit
- keep checkpoint storage separate from LangGraph execution semantics
- keep checkpoint body storage separate from Django metadata rows
- provide a durable foundation for future resume work without overfitting to a specific backend

## Target Semantics

Checkpoint semantics are not artifact semantics.

Target checkpoint capabilities:

- immutable version writes
- stable execution identity
- version ordering
- deterministic latest selection
- parent / lineage tracking
- serializer identity and version tracking
- idempotent retry
- conflict detection
- restart durability
- specific-version read
- history listing

## Target Value Model

Recommended checkpoint protocol shape:

- request / descriptor / read result separation
- immutable checkpoint versions
- explicit parent / lineage
- explicit serializer identity and version

Conceptual request:

```python
@dataclass(frozen=True, slots=True)
class CheckpointWriteRequest:
    run_id: int | str
    namespace: str
    checkpoint_id: str
    parent_checkpoint_id: str | None
    body: bytes = field(repr=False)
    serializer_name: str
    serializer_version: int
    metadata: Mapping[str, JsonValue] = field(default_factory=dict, repr=False)
```

Conceptual stored descriptor:

```python
@dataclass(frozen=True, slots=True)
class StoredCheckpoint:
    run_id: int | str
    namespace: str
    checkpoint_id: str
    parent_checkpoint_id: str | None
    revision: int | None
    serializer_name: str
    serializer_version: int
    size: int
    digest: str
    metadata: Mapping[str, JsonValue] = field(repr=False)
```

Conceptual read result:

```python
@dataclass(frozen=True, slots=True)
class CheckpointReadResult:
    checkpoint: StoredCheckpoint
    body: bytes = field(repr=False)
```

These shapes are design targets only. The current protocol does not define them.

## Identity Model

Recommended identity shape:

- execution identity: `(run_id, namespace)`
- checkpoint identity: `checkpoint_id`
- lineage parent: `parent_checkpoint_id`
- ordering: `revision`

The `run_id` alone is not sufficient for versioned checkpoint storage.

## Serialization Boundary

The checkpoint store should own bytes only.

Recommended boundary:

- execution / checkpointer adapter serializes state to bytes
- checkpoint store persists bytes and safe metadata only
- serializer identity and serializer version are persisted alongside the bytes

The store should not infer Python object structure or import serializer classes from arbitrary module paths.

## Target Filesystem Layout

If and when the protocol evolves, the first durable backend should use content-addressed immutable files and explicit head records.

Suggested layout:

```text
<root>/
  checkpoint-bodies/
    sha256/
      <shard>/
        <digest>.blob

  checkpoints/
    <run-digest>/
      <namespace-digest>/
        <checkpoint-id-digest>.json

  heads/
    <run-digest>/
      <namespace-digest>.json
```

This layout is provisional until identity and latest-selection semantics are finalized.

## Publication Order

Target publication order:

1. immutable state body
2. immutable checkpoint record
3. atomic head update

Failure bias:

- orphan body is allowed
- orphan checkpoint record is allowed
- missing or corrupt head references are not allowed

## Durability Scope

Target durability:

- `PROCESS_DURABLE`

Target scope:

- same host
- same filesystem root
- store recreation after process restart
- multiple store instances pointing at the same root

Not guaranteed:

- deployment durability
- power-loss durability
- multi-host semantics
- distributed consensus
- network filesystem behavior

## Failure Modeling

The future backend should distinguish:

- missing checkpoint
- corrupt record
- missing body
- unsupported serializer
- head corruption
- lost update
- conflicting concurrent append

Those failures should not collapse into a single generic missing-value result.

## Relationship To True Resume

Durable checkpoint storage is necessary but not sufficient for true resume.

True resume additionally needs:

- LangGraph adapter semantics
- pending writes / pending tasks
- interrupt and resume commands
- replay policy
- code / schema compatibility handling

## Deferred Work

- checkpoint protocol evolution is deferred
- filesystem checkpoint backend implementation is deferred
- checkpoint runtime selection is deferred
- true resume is deferred
- metadata orchestration is deferred
