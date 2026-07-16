# Durable Artifact Backend Design

This document defines the target design for the first durable artifact backend.

The implementation is not added in this block.
The design is now protocol-sufficient because `ArtifactStore` is body-aware and conflict-aware.
The protocol is now protocol-sufficient for backend implementation work.

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

- `StoreBackendConfig.backend = 'filesystem'`
- `StoreBackendConfig.config['root'] = <trusted filesystem root>`
- the factory receives the normalized store config and runtime context
- the backend must not read environment variables or Django settings directly

Current default behavior remains memory-backed and unchanged.

## Storage Layout

Target root layout:

```text
<root>/
  bodies/
    sha256/
      <shard>/
        <content-digest>
  records/
    <shard>/
      <storage-key-digest>.json
  tmp/
```

This layout preserves metadata / body separation.

### Mapping Rules

- logical storage keys stay opaque and validated
- record filenames are derived from a digest of the logical storage key
- body filenames are derived from a digest of the body content
- user-controlled storage keys must never be concatenated directly into paths

### Suggested Manifest Fields

- `schema_version`
- `storage_key`
- `run_id`
- `content_digest`
- `size`
- `content_type`
- `metadata`
- `created_at`

`schema_version` and `content_digest` are backend-internal or derivable until protocol evolution supplies a body-bearing seam.

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

- initial complexity: `O(number of records)`
- suitable for the first process-durable reference backend
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
- verify digest
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

This backend design is now protocol-sufficient.

The backend itself remains unimplemented in this block.

Default backend remains memory-backed `MemoryArtifactStore` until the filesystem backend is introduced explicitly.
