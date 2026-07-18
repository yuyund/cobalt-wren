# Checkpoint Store Contract

`CheckpointStore` is the versioned execution-state repository contract for durable checkpoint work.

Code is the source of truth.
Tests are the source of truth.
This document fixes the contract that durable backends must satisfy.

## Status

- protocol sufficiency decision: `APPROVED_FOR_IMPLEMENTATION`
- `MemoryCheckpointStore` is the EPHEMERAL semantic reference implementation
- `FilesystemCheckpointStore` is not yet implemented
- true resume remains deferred

## Execution Stream Identity

An execution stream is identified by:

- `run_id`
- `checkpoint_namespace`

Complete checkpoint identity is:

- `run_id`
- `checkpoint_namespace`
- `checkpoint_id`

`checkpoint_id` is caller-issued and identifies an immutable checkpoint version.
`revision` is store-assigned and defines deterministic ordering within a stream.
The store-assigned revision is the ordering key.
`parent_checkpoint_id` records lineage and acts as the expected current head precondition.
The contract is append-only and linear.
There is no delete operation in the versioned protocol.

## Value Types

The storage contract is split into three values:

- `CheckpointWriteRequest`
- `StoredCheckpoint`
- `CheckpointReadResult`

The caller owns serialization.
`CheckpointStore` persists bytes and safe metadata only.

## Write Contract

`save(request)` appends an immutable checkpoint version and advances the logical head.

Required write rules:

- validate the request before touching storage
- compare the full checkpoint identity before head / parent checks
- return the existing descriptor for an idempotent retry
- raise `CheckpointConflictError` for immutable identity conflicts
- treat `parent_checkpoint_id` as the expected current head
- reject stale parent writes
- assign revision numbers inside the store
- preserve a linear history per execution stream

Genesis rules:

- the first checkpoint in a stream uses `parent_checkpoint_id=None`
- the first revision in a stream is `1`
- a non-`None` parent on the first write is a conflict

## Read Contract

`load_latest(run_id, checkpoint_namespace=...)` reads the current head.
`load_checkpoint(run_id, checkpoint_id, checkpoint_namespace=...)` reads a specific version.
`list_for_run(run_id, checkpoint_namespace=...)` returns descriptors only, ordered by revision.

Read rules:

- missing latest / specific checkpoint returns `None`
- missing stream history returns `[]`
- `list_for_run()` does not return body bytes
- `load_latest()` and `load_checkpoint()` return descriptor plus body

## Serialization Contract

The store does not serialize or deserialize Python objects.

Accepted storage body:

- `bytes`

Stored descriptor metadata:

- serializer name
- serializer version
- content type
- safe JSON-compatible metadata

The store must not use import paths, dynamic serializer loading, or opaque Python objects as its persistence format.

## Delete Contract

- `delete(run_id)` is removed from the versioned protocol
- prune / retention / truncate are deferred to later work
- history must not be silently destroyed by the storage contract

## Memory Reference Implementation

`MemoryCheckpointStore` is:

- EPHEMERAL
- immutable version aware
- idempotent
- conflict aware
- thread-safe for same-process append
- linear in history

It is not restart durable.

## Durable Backend Target

`FilesystemCheckpointStore` is the first durable backend target.
It remains unimplemented in W2, but the protocol now allows a durable implementation to express:

- immutable version writes
- latest selection
- specific-version reads
- history listing
- parent / head preconditions
- serializer-aware descriptors

## Deferred Work

- filesystem backend implementation
- runtime backend selection
- Django orchestration
- reconciliation and retention
- true resume
