# Persistence Durability Contract

This document fixes the current and target contract for Artifact and Checkpoint persistence.

Code is the source of truth.
Tests are the source of truth.
Docs describe intent and the target contract.

## Scope

- Artifact body persistence
- Checkpoint body persistence
- Django metadata rows for artifacts and checkpoints
- safe metadata exposure across admin, UI, events, and errors
- durability, consistency, integrity, immutability, and idempotency expectations

## Non-Goals

- durable CheckpointStore implementation
- DB schema changes or migrations
- true resume
- run_workflow
- api.runtime
- worker / queue / outbox
- reconciliation worker
- cleanup command
- application workflow
- company_agent

## Metadata / Body Plane Separation

Artifact / checkpoint body-vs-metadata separation is a hard contract.

### Django metadata plane

Allowed:

- object identity
- run / workflow association
- thread / span association
- content type
- size
- checksum
- serializer / serializer version
- backend-safe reference
- timestamps
- safe summary

Forbidden:

- raw artifact body
- raw checkpoint body
- backend credentials
- provider raw object
- traceback
- secret-like values
- absolute local file path

### Body store plane

Allowed:

- artifact content
- checkpoint body
- serialized bytes or objects

Forbidden:

- metadata copy into body store as a substitute for content
- control-plane exposure of raw body
- backend credentials in metadata rows

## Durability Levels

- `EPHEMERAL`: survives only for the current process lifetime
- `PROCESS_DURABLE`: survives process restart in the same environment
- `DEPLOYMENT_DURABLE`: survives instance replacement and is shared across instances

### Current classification

- MemoryArtifactStore: `EPHEMERAL` `CODE_CONFIRMED`
- FilesystemArtifactStore: `PROCESS_DURABLE` `CODE_CONFIRMED`
- MemoryCheckpointStore: `EPHEMERAL` `CODE_CONFIRMED`

### Artifact backend runtime selection

- `stores.artifact` is the runtime selection boundary for built-in artifact backends
- section absence normalizes to `MemoryArtifactStore`
- explicit filesystem selection requires an absolute trusted root
- runtime selection is startup-only
- filesystem initialization errors fail startup instead of falling back to memory
- one filesystem root is one artifact identity domain

Evidence:

- `src/langgraph_automation/integrations/artifact/memory_store.py`
- `src/langgraph_automation/integrations/checkpoint/memory_store.py`
- `tests/unit/artifact/test_memory_store.py`
- `tests/unit/integrations/test_checkpoint_summary.py`

## Validation Harness

The reusable baseline contract suite lives in `tests/contract/persistence/` and exercises the public/provisional store methods as black-box behavior.

Characterization tests for current in-memory overwrite behavior stay in unit tests and do not define the shared baseline contract.

Advanced durable semantics remain deferred until durable backends exist.

## Object State Model

### ABSENT

- metadata absent
- body absent
- caller-visible result: missing object / `None`
- retryability: yes for create paths
- recovery: create a new object

### VALID

- metadata present
- body present
- read succeeds
- integrity can be verified

### ORPHAN_BODY

- body present
- metadata absent
- caller-visible result: not currently surfaced by the code path
- recovery: reconciliation or cleanup later

### DANGLING_METADATA

- metadata present
- body absent
- caller-visible result: read failure
- recovery: delete or repair later

### CORRUPT

- metadata present
- body present but deserialize or integrity check fails
- caller-visible result: read failure
- recovery: retry only if backend failure is transient; otherwise repair or delete later

## Current vs Target Write Model

### Current

- runtime assembly wires `MemoryArtifactStore` and `MemoryCheckpointStore`
- artifact backend selection is canonicalized through typed config and a single runtime builder
- `GraphRuntime` carries the stores
- no execution path currently writes artifact or checkpoint bodies through these store protocols
- Django observability emits metadata rows through `DjangoEventSink`
- `FilesystemArtifactStore` publishes content-addressed bodies and deterministic manifests on the local filesystem
- `FilesystemArtifactStore` verifies manifest integrity and body metadata during listing
- `FilesystemArtifactStore` verifies full body integrity on read
- `FilesystemArtifactStore` provides process-durable reads on the same host/root

Evidence:

- `src/langgraph_automation/apps/automation/services/runtime.py`
- `src/langgraph_automation/runtime/assembly.py`
- `src/langgraph_automation/graphs/runtime.py`
- `src/langgraph_automation/integrations/observability/django_event_sink.py`
- `rg -n "\\.put\\(|\\.save\\(|\\.load\\(|\\.delete\\(" src tests`

### Target baseline

1. validate input
2. apply safety validation
3. serialize body
4. write body immutably
5. verify write receipt / integrity
6. create metadata in a transaction
7. emit safe observability event

Preferred order:

- body first
- metadata second

Reason:

- body write failure must not create metadata
- metadata commit failure may create an orphan body, but must not create dangling metadata

### Gap

- current code wires in-memory stores only
- current code does not yet implement durable body writes or transactional body/metadata orchestration
- restart durability is therefore not guaranteed

## Immutability

### Artifact

Target:

- body immutable
- same identity with different content is a conflict
- content type, size, checksum preserved

Current:

- `MemoryArtifactStore.put()` is body-aware, immutable, idempotent, and conflict-aware
- `MemoryArtifactStore.get()` returns a descriptor plus body
- `MemoryArtifactStore.list_for_run()` returns descriptors only
- the current memory backend is still EPHEMERAL and does not provide restart durability
- `FilesystemArtifactStore` is PROCESS_DURABLE and restart-safe on the same host/root
- `FilesystemArtifactStore` uses content-addressed immutable body publication and deterministic manifests

Evidence:

- `src/langgraph_automation/integrations/artifact/memory_store.py`
- `tests/unit/artifact/test_memory_store.py`

### Checkpoint

Target:

- append-only or versioned
- no destructive overwrite of existing checkpoint body
- namespace / ordering / lineage preserved

Current:

- `MemoryCheckpointStore.save()` overwrites by `run_id`
- no versioning or lineage fields exist in the store protocol

Evidence:

- `src/langgraph_automation/integrations/checkpoint/base.py`
- `src/langgraph_automation/integrations/checkpoint/memory_store.py`

## Idempotency / Conflict

Target contract:

- same identity + same content => idempotent success
- same identity + different content => conflict
- different identity => new object

Current behavior:

- artifact store: idempotent success for canonical repeats and conflict for canonical differences
- checkpoint store: last write wins by run id
- no checksum-based idempotency check exists

## Integrity

Target metadata:

- size
- checksum
- serializer
- serializer version
- content type
- backend reference

Target read flow:

metadata lookup -> body read -> size/checksum verification -> deserialize -> caller

Forbidden:

- missing body treated as empty object
- corrupted body silently ignored
- checksum mismatch reduced to warning only
- unsupported serializer silently fallback-read

Current gap:

- `StoredArtifact` exposes `content_type`, `size`, `digest`, and `metadata`
- `CheckpointWriteResult` exposes `thread_id`, `checkpoint_namespace`, `backend`, `node_name`, `state_summary`, but no checksum, serializer, or backend reference

## Failure-Mode Matrix

Failure-mode matrix details live in `../../architecture/audit/PERSISTENCE_FAILURE_MODE_AUDIT.md`.

## Primary Failure Preservation

- EventSink failure must not overwrite primary persistence failure
- cleanup failure is out of scope and must not overwrite primary persistence failure
- safe error messages must not include traceback, backend credentials, or raw body content

Evidence:

- `src/langgraph_automation/integrations/observability/failure_policy.py`
- `src/langgraph_automation/apps/automation/services/runs.py`
- `src/langgraph_automation/graphs/runner.py`
- `tests/unit/automation/test_run_failure_observability_masking.py`
- `tests/unit/graphs/test_runner.py`

## Artifact Semantics

- identity: storage key
- current body plane: actual bytes body in the store
- current metadata plane: normalized stored descriptor
- overwrite behavior: current memory store is immutable per canonical request
- retention/delete: no durable backend behavior yet

## Checkpoint Semantics

- identity: run id in the current memory store, `checkpoint_id` in metadata
- current body plane: in-memory run state snapshot
- current metadata plane: `CheckpointMetadata` model
- overwrite behavior: current memory store overwrites by run id
- retention/delete: `delete()` removes the in-memory body only

## Backend Capability Matrix

| Capability | MemoryArtifactStore | MemoryCheckpointStore | Target durable backend |
| --- | --- | --- | --- |
| durability level | EPHEMERAL | EPHEMERAL | PROCESS_DURABLE or DEPLOYMENT_DURABLE |
| atomic object publication | no explicit guarantee | no explicit guarantee | required |
| conditional create | no | no | required |
| immutable write | yes | no | required |
| idempotent put | yes | no | required |
| checksum support | yes | no | required |
| size support | yes | no | required |
| listing | `list_for_run()` | no list API | required by use case |
| deletion | no | yes, in-memory only | required as a backend capability |
| versioning | no | no | required for checkpoint lineages |
| consistency model | process-local map | process-local map | explicit |
| shared access | no | no | required for deployment durability |
| restart behavior | lost on process restart | lost on process restart | preserved |
| credential handling | none | none | backend-specific, but not in metadata |
| encryption support | none | none | backend-specific |

## Deferred Work

- durable artifact/checkpoint backend is deferred
- api.runtime is deferred
- run_workflow is deferred
- application workflow is deferred
- company_agent is deferred
- true resume remains deferred and separate from storage durability
