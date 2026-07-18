# Durable Checkpoint Backend Design

This document describes the implemented durable checkpoint backend design.

Status: implemented and approved for implementation.

The checkpoint protocol expresses immutable checkpoint versions, lineage, serializer compatibility, specific-version reads, and history listing. The durable filesystem backend now realizes that contract locally.

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

The protocol uses the request / descriptor / read-result split:

- `CheckpointWriteRequest`
- `StoredCheckpoint`
- `CheckpointReadResult`

## Identity Model

Identity shape:

- execution identity: `(run_id, checkpoint_namespace)`
- checkpoint identity: `checkpoint_id`
- lineage parent: `parent_checkpoint_id`
- ordering: `revision`

`run_id` alone is not sufficient for versioned checkpoint storage.

## Serialization Boundary

The checkpoint store owns bytes only.

Recommended boundary:

- execution / checkpointer adapter serializes state to bytes
- checkpoint store persists bytes and safe metadata only
- accepted metadata is stored as a lossless logical JSON value
- persistence does not redact, mask, or drop accepted metadata values
- serializer identity and serializer version are persisted alongside the bytes

The store must not infer Python object structure or import serializer classes from arbitrary module paths.

## Filesystem Layout

The filesystem backend uses content-addressed bodies, stream-scoped records, and a mutable head record.

filesystem checkpoint backend is now implemented.
The record indexes are records/by-id and records/by-revision.
checkpoint runtime selection remains deferred to w4.

```text
<root>/
  bodies/
    sha256/
      <2>/
        <2>/
          <body-digest>.blob

  streams/
    sha256/
      <2>/
        <2>/
          <stream-digest>/
            lock
            head.json
            pending.json
            records/
              by-id/
                <2>/
                  <2>/
                    <checkpoint-id-digest>.json
              by-revision/
                00000000000000000001.json
                00000000000000000002.json
```

Raw `run_id`, `checkpoint_namespace`, `checkpoint_id`, and `parent_checkpoint_id` never appear as path components.

## Publication Order

Target publication order:

1. immutable state body
2. pending append intent
3. immutable checkpoint record by id
4. the same immutable record by revision
5. atomic head update
6. pending cleanup
7. directory fsync

Failure bias:

- orphan body is allowed
- orphan checkpoint record is allowed
- missing or corrupt head references are not allowed once recovery runs

## Crash-Window Recovery

The backend uses a stream-local pending record to recover between immutable record publication and mutable head advancement.

Recovery handles:

- pending only
- by-id only
- by-revision only
- both indexes with an old head
- head already at the pending target

Impossible combinations raise `CheckpointIntegrityError`.

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

The filesystem backend distinguishes:

- missing checkpoint
- corrupt record
- missing body
- unsupported serializer
- head corruption
- lost update
- conflicting concurrent append

Those failures do not collapse into a single generic missing-value result.

## Relationship To True Resume

Durable checkpoint storage is necessary but not sufficient for true resume.

True resume additionally needs:

- LangGraph adapter semantics
- pending writes / pending tasks
- interrupt and resume commands
- replay policy
- code / schema compatibility handling

## Deferred Work

- checkpoint runtime selection
- true resume
- metadata orchestration
