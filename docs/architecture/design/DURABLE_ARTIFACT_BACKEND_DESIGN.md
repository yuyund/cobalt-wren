# Durable Artifact Backend Design

This document defines the design for the first durable artifact backend.

The implementation now lives in `src/cobalt_wren/integrations/artifact/filesystem_store.py`.
The design remains the reference contract for that backend.

## Selected Backend Candidate

- backend: `FilesystemArtifactStore`
- durability: `PROCESS_DURABLE`
- deployment scope: single host, same filesystem root, multiple processes/instances on that host

## Rejected or Deferred Alternatives

- Django database body storage: deferred because it increases ORM coupling and does not match the first durable backend target
- remote object storage: deferred as a later `DEPLOYMENT_DURABLE` backend
- checkpoint durability: out of scope for this block

## Dependency Boundary

The backend must depend only on:

- the artifact store protocol surface
- standard library filesystem primitives
- safe redaction / summary helpers where needed

It must not import:

- Django
- `apps.automation`
- `graphs.runner`
- `workflows`
- admin or web UI modules

## Configuration Boundary

The backend root must be injected by trusted configuration.

Target integration shape:

- `stores.artifact.backend = 'filesystem'`
- `stores.artifact.config.root = <trusted filesystem root>`
- raw package config normalizes into typed artifact store settings
- the canonical runtime builder constructs the backend exactly once per runtime assembly
- the backend must not read environment variables or Django settings directly
- section absence normalizes to `MemoryArtifactStore`
- filesystem selection is explicit opt-in and startup-only

Current default behavior remains memory-backed and unchanged.

## Storage Layout

Target root layout:

```text
<root>/
  bodies/
    sha256/
      <shard>/
        <content-digest>.blob
  records/
    sha256/
      <shard>/
        <storage-key-digest>.json
```

This layout preserves metadata / body separation.

### Mapping Rules

- logical storage keys stay opaque and validated
- record filenames are derived from a digest of the logical storage key
- body filenames are derived from a digest of the body content
- user-controlled storage keys must never be concatenated directly into paths

### Suggested Manifest Fields

- `schema_version`
- `run_id`
- `storage_key`
- `name`
- `kind`
- `content_type`
- `size`
- `digest`
- `metadata`

`schema_version` and `digest` are backend-internal and are now encoded in the filesystem manifest contract.

## Write Flow

Target order:

1. validate logical input
2. normalize/serialize body
3. compute size and digest
4. write temporary body file in the same filesystem
5. flush and fsync as required by the durability target
6. publish immutable body without destructive overwrite
7. create canonical record manifest
8. publish manifest without destructive overwrite
9. return the protocol result

Preferred publication primitive:

- temp file + hard-link publication on the same filesystem

Why:

- immutable no-overwrite publication
- concurrent writers can detect existing targets deterministically
- partial file exposure is minimized compared with direct overwrite

`os.replace()` is not treated as immutable publication because it is destructive overwrite.

## Read Flow

Target order:

1. validate storage key
2. resolve record manifest
3. parse schema version
4. verify logical key binding
5. locate content-addressed body
6. read body
7. verify size
8. verify digest
9. reconstruct the protocol result

Missing or corrupt artifacts must fail safely.
They must not be returned as empty objects.

## List Semantics

`list_for_run(run_id)` can initially scan manifests and filter by `run_id`.

This is intentionally simple:

- initial complexity: `O(number of records + manifest bytes + filesystem stat operations)`
- suitable for the first process-durable reference backend
- body content is not read or digest-verified during listing
- future optimization: per-run index, database index, or object-store listing

## Immutability, Idempotency, Conflict

Target semantics:

- same-key/same-content: idempotent success
- same-key/different-content: deterministic conflict
- different logical storage key: independent record

The backend should reuse content-addressed bodies when content digests match.

## Integrity

Target contract:

- verify manifest structure
- verify logical key binding
- verify size
- verify body existence and regular-file metadata during listing
- verify digest during `get()`
- verify schema version compatibility

Failure modes:

- missing manifest: normal missing-object behavior
- missing body: safe integrity failure
- digest mismatch: safe integrity failure
- invalid manifest: safe corruption failure
- unsupported schema version: safe compatibility failure

## Restart and Concurrency

Target guarantees:

- process restart can re-open the same root and read stored artifacts
- multiple store instances on the same host and same root can share artifacts
- concurrent same-key/same-content writes converge to success
- concurrent same-key/different-content writes converge to deterministic conflict

Not guaranteed:

- multi-host deployment
- instance replacement across different roots
- distributed transaction semantics

## Safe Errors

Backend errors must not expose:

- filesystem absolute root
- temporary path
- raw body
- secret-like metadata
- traceback
- credential-bearing config

Safe diagnostics may include:

- operation name
- safe logical identifier or bounded digest
- safe error category

## Internal Manifest vs Django Metadata

The backend manifest is internal to the filesystem store.

It is not the same thing as Django `Artifact` metadata.
The design keeps metadata / body separation explicit.

Current orchestration remains deferred:

- no body write plus Django transaction integration
- no body/metadata coordination service
- no orphan cleanup worker
- no dangling metadata repair worker

## Non-Goals

- durable checkpoint backend
- Django model creation
- Django transaction orchestration
- EventSink persistence
- Run lifecycle changes
- graph execution changes
- UI/admin rendering changes
- cleanup or reconciliation workers
- remote object storage

## Protocol Dependency

This backend design is now implemented.

Default backend remains memory-backed `MemoryArtifactStore`.
