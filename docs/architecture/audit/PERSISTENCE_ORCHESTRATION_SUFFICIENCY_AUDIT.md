# Persistence Orchestration Sufficiency Audit

This audit determines whether the current execution lifecycle is sufficient to orchestrate artifact and checkpoint persistence safely.

Code is the source of truth.
Tests are the source of truth.
This document records the current production flow, the installed LangGraph adapter surface, and the remaining orchestration gaps.

## Executive Decision

Current execution lifecycles do not yet persist artifacts or checkpoints.

The durable backend layer is complete, but execution persistence orchestration is not.

Final decision:

- artifact orchestration: `NEEDS_PUBLIC_OR_PLUGIN_CONTRACT`, `BLOCKED_BY_ARTIFACT_IDENTITY`, and `NEEDS_INTERNAL_ORCHESTRATION_CONTRACT`
- checkpoint adapter: `BLOCKED_BY_PENDING_WRITES` and `BLOCKED_BY_RUN_THREAD_MAPPING`
- control-plane projection: `BLOCKED_BY_CONTROL_PLANE_SCHEMA`
- true resume: not approved

Recommended target model:

- explicit artifact emission only
- caller-owned serialization
- package-runtime-owned store calls
- application-adapter-owned control-plane projection
- separate LangGraph checkpoint adapter before true resume

Configuration ownership note:

- physical persistence configuration is bound once at application composition
- the production deployment source is `LANGGRAPH_AUTOMATION` in Django settings, loaded once by `AutomationConfig.ready()`
- `NormalizedPackageConfig` is not accepted as a per-run override on `start_run()` / `retry_run()`
- `RunExecutionServices` owns the bound runtime factory for the production run path
- workflow / run payloads remain validation-only inputs and cannot rebuild store selection

Deployment startup binding note:

- `AutomationConfig.ready()` binds services exactly once per composition instance for a given raw deployment config
- repeated `ready()` calls with the same deployment config are no-ops
- repeated `ready()` calls with a different deployment config fail closed
- invalid deployment config fails startup before any runtime services are published

Legacy deployment data note:

- repository scans show workflow payload `stores` shapes only in tests and docs
- local DB inspection in the current workspace snapshot was unavailable because the automation tables were not present
- persisted deployment status remains `UNKNOWN` until a deployment-backed preflight or migrated database snapshot is inspected

## Scope

In scope:

- canonical production execution path
- `RuntimeDependencies` propagation
- run lifecycle and DB transaction boundaries
- artifact ownership and identity analysis
- installed LangGraph checkpoint API inventory
- checkpoint adapter compatibility analysis
- `run_id` / `thread_id` / `checkpoint_namespace` mapping
- pending writes and protocol gaps
- safe control-plane projection
- failure / retry / cancellation semantics
- next implementation block sequencing

Out of scope:

- execution persistence implementation
- `ArtifactStore.put()` execution wiring
- `CheckpointStore.save()` execution wiring
- LangGraph adapter implementation
- Django schema changes
- model migrations
- `run_workflow`
- `api.runtime`
- true resume

## Code-First Source Inventory

### Package execution and runtime

- `src/langgraph_automation/apps/automation/services/runs.py`
- `src/langgraph_automation/apps/automation/services/execution.py`
- `src/langgraph_automation/apps/automation/services/runtime.py`
- `src/langgraph_automation/workflows/prepare.py`
- `src/langgraph_automation/workflows/adapter.py`
- `src/langgraph_automation/graphs/builders.py`
- `src/langgraph_automation/graphs/runner.py`
- `src/langgraph_automation/graphs/runtime.py`
- `src/langgraph_automation/runtime/assembly.py`
- `src/langgraph_automation/runtime/dependencies.py`
- `src/langgraph_automation/runtime/artifact_store.py`
- `src/langgraph_automation/runtime/checkpoint_store.py`

### Application and control-plane

- `src/langgraph_automation/apps/automation/models/run.py`
- `src/langgraph_automation/apps/automation/models/execution.py`
- `src/langgraph_automation/apps/automation/models/artifact.py`
- `src/langgraph_automation/apps/automation/models/checkpoint.py`
- `src/langgraph_automation/apps/automation/models/event.py`
- `src/langgraph_automation/apps/automation/policies/runs.py`
- `src/langgraph_automation/integrations/observability/base.py`
- `src/langgraph_automation/integrations/observability/django_event_sink.py`
- `src/langgraph_automation/integrations/observability/types.py`

### Installed LangGraph source

- `venv/lib/python3.12/site-packages/langgraph/checkpoint/base/__init__.py`
- `venv/lib/python3.12/site-packages/langgraph/checkpoint/memory/__init__.py`

## Canonical Production Execution Call Graph

### Primary production path

`application composition`
  -> `src/langgraph_automation/apps/automation/services/runtime.py:build_run_execution_services`
  -> `src/langgraph_automation/apps/automation/services/runtime.py:ApplicationRuntimeFactory`
  -> `src/langgraph_automation/apps/automation/services/runtime.py:RunExecutionServices`
  -> `src/langgraph_automation/apps/automation/services/runs.py:start_run`
  -> `src/langgraph_automation/apps/automation/services/runs.py:_make_runtime`
  -> `src/langgraph_automation/apps/automation/services/runtime.py:RunExecutionServices.build_graph_runtime`
  -> `src/langgraph_automation/apps/automation/services/runtime.py:ApplicationRuntimeFactory.build_graph_runtime`
  -> `src/langgraph_automation/apps/automation/services/runtime.py:build_graph_runtime`
  -> `src/langgraph_automation/apps/automation/services/runtime.py:build_event_sink`
  -> `src/langgraph_automation/apps/automation/services/runtime.py:build_artifact_store`
  -> `src/langgraph_automation/apps/automation/services/runtime.py:build_checkpoint_store`
  -> `src/langgraph_automation/apps/automation/services/execution.py:dispatch_run_execution`
  -> `src/langgraph_automation/graphs/runner.py:LangGraphRunner.run_graph_once`
  -> `src/langgraph_automation/graphs/runner.py:LangGraphRunner._invoke_graph`
  -> `langgraph graph.invoke(...)`
  -> `src/langgraph_automation/apps/automation/services/runs.py:_finalize_from_execution`

Classification:

- `CANONICAL_PRODUCTION`

Observed characteristics:

- sync execution
- short DB transaction before execution
- short DB transaction after execution
- no artifact persistence call
- no checkpoint persistence call
- `GraphRuntime` carries artifact/checkpoint stores, but the runner does not use them for persistence

### Alternate production path

`src/langgraph_automation/apps/automation/services/workflow_preparation.py`
  -> `langgraph_automation.api.engine`
  -> `src/langgraph_automation/api/engine.py:create_engine`
  -> `src/langgraph_automation/runtime/assembly.py:RuntimeAssembler.assemble`
  -> `src/langgraph_automation/runtime/dependencies.py:RuntimeDependencies`
  -> `src/langgraph_automation/workflows/prepare.py:WorkflowPreparer.prepare`

Classification:

- `ALTERNATE_PRODUCTION`

Observed characteristics:

- application-side workflow preparation only
- no graph execution
- no persistence write path
- `RuntimeDependencies` is consumed for workflow requirements and graph construction, not execution persistence

### Test and future paths

- `src/langgraph_automation/graphs/runner.py:resume_graph_once` -> `NotImplementedError`
- `src/langgraph_automation/apps/automation/services/runs.py:resume_run` -> `NotImplementedError`

Classification:

- `DEAD_OR_UNUSED`

## Runtime Dependency Propagation

`RuntimeAssembler.assemble()` constructs `RuntimeDependencies` once from normalized config.

Propagation path:

`src/langgraph_automation/runtime/assembly.py:RuntimeAssembler.assemble`
  -> `src/langgraph_automation/runtime/dependencies.py:RuntimeDependencies`
  -> `src/langgraph_automation/api/engine.py:AutomationEngine`
  -> `src/langgraph_automation/workflows/prepare.py:WorkflowPreparer.prepare`
  -> `src/langgraph_automation/workflows/requirements.py:check_workflow_requirements`

For the execution plane, the actual owner is `GraphRuntime`, but its store selection is now owned by a composition-bound runtime services object:

`src/langgraph_automation/apps/automation/services/runtime.py:build_graph_runtime`
  -> `src/langgraph_automation/graphs/runtime.py:GraphRuntime`
  -> `src/langgraph_automation/apps/automation/services/execution.py:dispatch_run_execution`
  -> `src/langgraph_automation/graphs/runner.py:LangGraphRunner`

The application runtime selects artifact and checkpoint stores from trusted normalized package settings that were bound once into `RunExecutionServices`, and delegates construction to the canonical runtime builders before handing the exact instances to `GraphRuntime`.
Workflow payload physical persistence config is rejected at validation time, so it cannot source backend selection or filesystem roots.

Classification:

- `RuntimeDependencies.artifact_store`: `REACHES_APPLICATION_ONLY`
- `RuntimeDependencies.checkpoint_store`: `REACHES_APPLICATION_ONLY`
- `GraphRuntime.artifact_store`: `REACHES_EXECUTION_OWNER_UNUSED`
- `GraphRuntime.checkpoint_store`: `REACHES_EXECUTION_OWNER_UNUSED`

The current execution owner receives the selected stores, but no production code uses them to persist artifacts or checkpoints yet.

## Run Lifecycle Matrix

| From | Trigger | To | DB transaction | External execution |
| --- | --- | --- | --- | --- |
| `pending` | `start_run()` accepted | `running` | short `transaction.atomic()` | execution begins after the transaction |
| `running` | `dispatch_run_execution()` returns success | `succeeded` | short `transaction.atomic()` | execution completed |
| `running` | `dispatch_run_execution()` returns failure | `failed` | short `transaction.atomic()` | execution stopped |
| `pending` or `running` | `cancel_run()` accepted | `cancelled` | short `transaction.atomic()` | cancellation notification happens after commit |
| `failed` or `cancelled` | `retry_run()` accepted | `running` | short `transaction.atomic()` | execution begins after the transaction |
| any | `resume_run()` called | none | none | `NotImplementedError` |

Additional facts:

- `Run` primary identity is the database integer PK.
- `thread_id` is stored on the `Run` row and initialized to `run-{pk}` when blank.
- `ExecutionSpan.attempt` exists, but `Run` does not have an attempt counter.
- long-running graph execution happens outside the DB transaction.
- there is no transaction wrapping graph execution, filesystem I/O, or store composition.

## Artifact Data Classification

| Candidate | Classification | Current producer | Current consumer | Persistence expectation |
| --- | --- | --- | --- | --- |
| graph final result | `GRAPH_STATE` | `LangGraphRunner._invoke_graph` | `runs._finalize_from_execution` | not automatically persisted to artifact storage |
| graph final state | `GRAPH_STATE` | graph runtime | graph runner | not persisted |
| node output | `GRAPH_STATE` or `DIAGNOSTIC` | graph nodes | graph runtime / observability | not automatically persisted |
| tool output | `SENSITIVE_AUTO_PERSIST_FORBIDDEN` | tool nodes | observability summary helpers | only summarized metadata |
| generated file | `ARTIFACT` when explicitly emitted | future explicit artifact producer | future artifact orchestrator | explicit only |
| report / document | `ARTIFACT` when explicitly emitted | future explicit artifact producer | future artifact orchestrator | explicit only |
| workflow-defined artifact | `ARTIFACT` when explicitly emitted | workflow/plugin/application | future artifact orchestrator | explicit only |
| debug trace | `DIAGNOSTIC` | observability/runtime | event sink | bounded only |
| event payload | `CONTROL_PLANE_METADATA` | sinks / services | Django rows | safe projection only |
| application attachment | `UNDEFINED_CONTRACT` | application code | not defined | not yet contracted |

Current code does not auto-classify or auto-save artifacts from graph return values.

## Artifact Ownership And Identity

### Current state

- `ArtifactStore` exists and is body-aware.
- `ArtifactWriteRequest` carries `run_id`, `storage_key`, `body`, `name`, `kind`, `content_type`, and metadata.
- `StoredArtifact` carries normalized descriptor fields plus size and digest.
- `MemoryArtifactStore` and `FilesystemArtifactStore` already provide idempotent and conflict-aware writes.
- current production execution path does not create `ArtifactWriteRequest` instances.
- current artifact identity is `storage_key` plus canonical body and metadata comparison
- same identity / same canonical request is idempotent in the store layer
- same identity / different canonical request is a conflict in the store layer

### Recommended target ownership

- artifact emission owner: workflow / plugin / application code that produced the candidate
- artifact serialization owner: caller or emitter
- artifact identity owner: caller or emitter, usually via a logical `storage_key`
- artifact store call owner: package runtime orchestration
- control-plane projection owner: application adapter

### Failure policy recommendation

- explicit required artifact: persistence failure should fail the execution
- optional artifact: future explicit contract only
- silent drop: forbidden
- backend fallback: forbidden

### Readiness

- artifact orchestration is not yet ready because there is no canonical emission owner in the execution lifecycle
- artifact protocol itself is sufficient for implementation

## Installed LangGraph Checkpointer API Inventory

Installed versions:

- `langgraph==1.2.9`
- `langgraph-checkpoint==4.1.1`

Relevant source:

- `langgraph.checkpoint.base`
- `langgraph.checkpoint.memory`

Observed base API:

| Method | Signature shape | Notes |
| --- | --- | --- |
| `get` | `get(config: RunnableConfig) -> Checkpoint | None` | sync |
| `aget` | async wrapper | sync-to-async bridge |
| `get_tuple` | `get_tuple(config: RunnableConfig) -> CheckpointTuple | None` | sync |
| `aget_tuple` | async wrapper | sync-to-async bridge |
| `list` | `list(config: RunnableConfig | None, *, filter=None, before=None, limit=None) -> Iterator[CheckpointTuple]` | supports ordering and filtering |
| `alist` | async wrapper | sync-to-async bridge |
| `put` | `put(config, checkpoint, metadata, new_versions) -> RunnableConfig` | sync |
| `aput` | async wrapper | sync-to-async bridge |
| `put_writes` | `put_writes(config, writes, task_id, task_path='') -> None` | pending writes |
| `aput_writes` | async wrapper | sync-to-async bridge |
| `delete_thread` | `delete_thread(thread_id: str) -> None` | destructive thread delete |
| `adelete_thread` | async wrapper | sync-to-async bridge |
| `delete_for_runs` | `delete_for_runs(run_ids: Sequence[str]) -> None` | destructive run delete |
| `adelete_for_runs` | async wrapper | sync-to-async bridge |
| `copy_thread` | thread copy helper | present in the installed API |
| `acopy_thread` | async wrapper | sync-to-async bridge |
| `prune` | pruning helper | present in the installed API |
| `aprune` | async wrapper | sync-to-async bridge |
| `get_delta_channel_history` | `get_delta_channel_history(*, config: RunnableConfig, channels: Sequence[str])` | delta history helper |
| `aget_delta_channel_history` | async wrapper | sync-to-async bridge |
| `get_next_version` | `get_next_version(current, channel) -> V` | version generation hook |
| `config_specs` | property | required config keys |
| `serde` | serializer helper | serializer boundary |

Relevant installed types:

- `RunnableConfig`
- `Checkpoint`
- `CheckpointMetadata`
- `CheckpointTuple`
- `ChannelVersions`

### Observed LangGraph checkpoint semantics

- `thread_id` is the primary lookup key in the installed saver API.
- `checkpoint_ns` is part of the config shape.
- `checkpoint_id` is part of the config shape.
- `pending_writes` is a first-class LangGraph concern.
- async methods are part of the public installed API, even when they delegate to sync implementations.

## Checkpoint Adapter Compatibility Matrix

| LangGraph concept / API | Current framework candidate | Compatibility | Gap |
| --- | --- | --- | --- |
| `thread_id` | `run_id` / `Run.thread_id` | `SUPPORTED_BY_ADAPTER` only | execution identity and thread identity are distinct in current code |
| `checkpoint_ns` | `checkpoint_namespace` | `SUPPORTED_BY_ADAPTER` | namespace policy is not yet specified for nested graphs |
| `checkpoint_id` | `checkpoint_id` | `SUPPORTED_DIRECTLY` at storage layer | adapter still needs config reconstruction |
| parent config | `parent_checkpoint_id` | `SUPPORTED_BY_ADAPTER` | checkpoint config synthesis still missing |
| checkpoint body | `body: bytes` | `SUPPORTED_DIRECTLY` at storage layer | adapter must serialize / deserialize |
| checkpoint metadata | request metadata | `SUPPORTED_DIRECTLY` at storage layer | semantics need adapter mapping |
| latest lookup | `load_latest()` | `SUPPORTED_DIRECTLY` at storage layer | LangGraph config shape still missing |
| specific lookup | `load_checkpoint()` | `SUPPORTED_DIRECTLY` at storage layer | adapter still missing |
| listing | `list_for_run()` | `SUPPORTED_DIRECTLY` at storage layer | `before` / `limit` / filter bridging missing |
| `put` | `save()` | `SUPPORTED_BY_ADAPTER` | adapter must translate `RunnableConfig` to request |
| `put_writes` | none | `BLOCKED_BY_PENDING_WRITES_CONTRACT` | pending writes are not modeled in current `CheckpointStore` |
| async API | sync store | `SUPPORTED_BY_ADAPTER` | thread wrapper or native async needed for async execution |
| delete thread | no delete | `OUT_OF_SCOPE` | deletion was intentionally removed from the checkpoint store contract |
| version generation | store revision | `SUPPORTED_DIRECTLY` at storage layer | adapter must not reinterpret revision as LangGraph version identity |

### Readiness decision

- current checkpoint storage protocol is ready for a future adapter
- current code is not ready for a full LangGraph checkpoint adapter
- pending writes remain an open blocker for true resume

## run_id / thread_id Analysis

Current state:

- `run_id` is the database integer PK on `Run`
- `thread_id` is a separate string field on `Run`
- `thread_id` is assigned as `run-{pk}` when the run starts if the field is empty
- the runtime observability context carries `run_id` and `thread_id` separately

Decision:

- `OPTION_2_REQUIRED`

Reason:

- the code already keeps run identity and thread identity separate
- the adapter boundary needs an explicit mapping owner
- retry, rerun, and resume are distinct lifecycle ideas in the current codebase

Terminology:

- same operation retry: reattempt after transport or persistence failure
- execution attempt retry: `retry_run()`
- node retry: not yet modeled in the execution path
- rerun: a new lifecycle execution of the same workflow
- resume: deferred until checkpoint adapter semantics exist

## Checkpoint Namespace Analysis

Current state:

- storage protocol has `checkpoint_namespace`
- Django checkpoint metadata rows currently default the namespace to `''`
- no production execution path currently maps LangGraph subgraph namespace semantics into the store

Decision:

- `REQUIRES_NAMESPACE_POLICY`

Reason:

- the store can carry the namespace, but the adapter policy is not yet defined
- nested graph and subgraph mapping are not yet implemented

## Sync / Async Decision

Decision:

- `SYNC_ONLY_INITIAL_SCOPE`

Reason:

- the current production execution path is synchronous
- the installed LangGraph checkpointer API exposes async methods, but the current codebase does not use async graph execution in production
- a later adapter can either wrap the sync store in threads or add native async support

## Pending Writes Decision

Decision:

- `BLOCKED_BY_PENDING_WRITES_CONTRACT`

Reason:

- the installed LangGraph API exposes `put_writes` and `pending_writes`
- the current `CheckpointStore` protocol intentionally excludes pending writes
- true resume cannot be approved without a pending-write strategy
- the separate-store-vs-protocol choice remains open and is deferred to `X3`

## Serialization Ownership

Current contract:

- caller or adapter serializes Python state to bytes
- store persists bytes and safe descriptors
- store does not deserialize arbitrary objects

Ownership split:

- LangGraph checkpoint object -> bytes: adapter
- bytes -> LangGraph checkpoint object: adapter
- serializer name/version/content type: adapter or caller
- store responsibility: persistence, integrity, revision, idempotency

## Failure, Retry, And Cancellation Matrices

### Cross-system failure / atomicity

| Failure point | Durable store | DB / control-plane | Run status | Retry requirement |
| --- | --- | --- | --- | --- |
| execution start before persistence | none | run exists or not yet created | pending | normal |
| serialization before store call | none | running | running | same identity |
| store write before DB reference | object exists or partial write | no reference | running / failed | idempotent store retry |
| store write after success but before DB projection | durable object exists | stale metadata | running / failed | recovery / reconciliation later |
| DB projection after store write | durable object + reference | stale status possible | running | status recovery |
| success status after event failure | durable object + success status | success | succeeded | event policy only |
| checkpoint commit after crash | checkpoint may exist | stale run row | running | adapter idempotency |

Current code does not implement this orchestration yet.

### Retry matrix

| Retry type | Run identity | Artifact identity | Checkpoint identity | Expected behavior |
| --- | --- | --- | --- | --- |
| same store call retry | same | same storage key | same checkpoint id | idempotent if same canonical request |
| execution service retry | same run row | not yet specified | not yet specified | explicit orchestration needed |
| node retry | same logical execution | future emitter policy | LangGraph-managed | adapter owned |
| rerun | new logical execution | new or remapped | new or remapped | new history |
| resume | same logical thread | future policy | descendant / current head | future |

### Cancellation matrix

| Cancellation point | Store state | DB state | Required handling |
| --- | --- | --- | --- |
| before serialization | none | running | cancelled |
| during serialization | none | running | no committed persistence |
| during store write | backend-defined | running | next retry / recovery |
| after store commit | durable object | no reference | reconciliation candidate |
| after DB reference | durable + reference | running | status policy |
| during checkpoint callback | possible committed version | running | adapter semantics |

Committed immutable objects are not deleted by cancellation.

## Control-Plane Safe Projection

### Artifact safe fields

- safe storage reference
- run foreign key
- logical artifact kind / label
- content type
- size
- digest
- serializer or format descriptor if applicable
- backend durability classification
- created timestamp

### Checkpoint safe fields

- safe stream reference
- run / thread mapping reference
- checkpoint namespace safe representation
- revision
- serializer name
- serializer version
- content type
- size
- digest
- created timestamp

### Forbidden projection payload

- body bytes
- graph state
- prompt
- raw tool output
- secret-like metadata
- full filesystem path
- root path
- arbitrary serializer payload
- raw exception cause

Current Django schema is not sufficient for a complete checkpoint projection.

Decision:

- `BLOCKED_BY_CONTROL_PLANE_SCHEMA`

## EventSink Exposure Analysis

Current `EventSink` contract carries safe payloads only.

Current `DjangoEventSink` projections:

- `artifact_created()` writes a metadata-only `Artifact` row
- `checkpoint_saved()` writes a metadata-only `CheckpointMetadata` row
- raw body bytes do not flow through the event sink
- summary helpers bound and redact payloads before persistence

Safe future envelope:

- artifact persisted event: safe reference, size, content type, backend kind
- checkpoint persisted event: safe stream reference, revision, serializer descriptor

Forbidden payload:

- body
- graph state
- raw metadata values
- raw IDs when avoidable
- filesystem paths
- root
- raw exception text

## Error Taxonomy Propagation

Current error families:

- `ArtifactValidationError`
- `ArtifactConflictError`
- `ArtifactIntegrityError`
- `ArtifactPersistenceError`
- `CheckpointValidationError`
- `CheckpointConflictError`
- `CheckpointIntegrityError`
- `CheckpointPersistenceError`

Propagation rules:

- validation: request/config issue
- conflict: identity mismatch or stale head
- integrity: durable state corruption
- persistence: infrastructure / I/O failure
- safe messages only
- no raw body / metadata / path / traceback in public messages

The execution layer currently surfaces run failures through `safe_run_error_message()` and `safe_run_output_payload()`, not through persistence errors.

## Boundary And Public API Analysis

Current public store facade:

- `src/langgraph_automation/api/stores.py`

Current concrete integration exports:

- `src/langgraph_automation/integrations/checkpoint/__init__.py`
- `src/langgraph_automation/integrations/artifact/__init__.py`

Current boundary posture:

- no public execution API
- no `api.runtime`
- no generic persistence orchestrator
- no top-level `langgraph_automation.CheckpointStore` re-export
- no top-level `langgraph_automation.ArtifactStore` re-export

Execution persistence should remain behind a package-internal orchestrator and a future LangGraph adapter.

## Gap Classification

| Gap | Affected component | Evidence | Consequence | Minimum next change | Public API impact | Migration impact | Ordering dependency | Classification |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| no execution persistence calls | `runs.py`, `execution.py`, `runtime.py`, `graphs/runner.py` | code-first call graph | artifacts/checkpoints are not persisted from execution | add an explicit orchestration contract | none yet | none yet | before any save wiring | `NEEDS_INTERNAL_ORCHESTRATION_CONTRACT` |
| artifact emission owner undefined | workflow / application layer | no explicit emission site exists | no stable artifact identity owner | define emission owner and logical slot policy | possible later facade addition | none yet | before artifact save wiring | `NEEDS_PUBLIC_OR_PLUGIN_CONTRACT` |
| checkpoint adapter missing | package / LangGraph boundary | storage contract differs from LangGraph `BaseCheckpointSaver` | no adapter to runtime config shape | define adapter contract and mapping | possible adapter facade later | none yet | before resume | `BLOCKED_BY_PENDING_WRITES` |
| thread mapping not isolated | run model / checkpoint adapter | `Run.thread_id` is separate from `Run.pk` | no explicit lifecycle mapping owner | define mapping owner and stable policy | none yet | none yet | before adapter | `BLOCKED_BY_RUN_THREAD_MAPPING` |
| checkpoint namespace policy missing | adapter / subgraph integration | no subgraph policy exists | namespace semantics can drift | define namespace reconstruction policy | none yet | none yet | before adapter | `REQUIRES_NAMESPACE_POLICY` |
| control-plane projection incomplete | Django models / sink | rows are metadata-only | no durable safe reference table for the new persistence boundary | extend projection schema or add a new model | migration later | yes later | after orchestration contract | `BLOCKED_BY_CONTROL_PLANE_SCHEMA` |
| pending writes absent | LangGraph adapter | installed API exposes `put_writes` and `pending_writes` | true resume is not expressible | separate pending-write contract or protocol evolution | later adapter surface | maybe later | before true resume | `BLOCKED_BY_PENDING_WRITES_CONTRACT` |
| async adapter not defined | adapter / execution mode | installed API includes async methods | async graph execution bridge is unclear | define sync-only initial scope or thread wrapper | no public API yet | none yet | before async adapter | `OUT_OF_INITIAL_SCOPE` |

## Recommended Implementation Sequence

1. `X2` Artifact Emission and Identity Contract
   - objective: define who emits artifacts and what the stable artifact identity is
   - prerequisites: none
   - production changes: none
   - non-goals: execution wiring and DB schema changes

2. `X3` Pending Write and Checkpoint Identity Protocol Design
   - objective: define the adapter contract between LangGraph and `CheckpointStore`, including pending-write handling and run/thread mapping policy
   - prerequisites: current checkpoint storage contract
   - production changes: none
   - non-goals: true resume implementation

3. `X4` Artifact Persistence Orchestration Implementation
   - objective: wire explicit artifact emission through the chosen orchestrator
   - prerequisites: emission owner and identity contract
   - production changes: orchestration only
   - non-goals: checkpoint adapter

4. `X5` Artifact Control-Plane Reference Projection
   - objective: persist safe artifact references in the control plane
   - prerequisites: artifact emission and identity contract
   - production changes: control-plane projection only
   - non-goals: raw body persistence in Django

5. `X6` Sync LangGraph Checkpointer Adapter
   - objective: bridge LangGraph checkpoint semantics to `CheckpointStore` for the initial sync scope
   - prerequisites: adapter contract and pending-write decision
   - production changes: adapter only
   - non-goals: true resume unless pending-write semantics exist

6. `X7` Reconciliation and Resume Hardening
   - objective: reconcile durable store objects with control-plane references and harden resume semantics
   - prerequisites: orchestration, adapter, and projection contracts
   - production changes: recovery / reconciliation only
   - non-goals: new persistence protocols

## Final Readiness Decision

Artifact:

- orchestration readiness: `NEEDS_PUBLIC_OR_PLUGIN_CONTRACT` and `BLOCKED_BY_ARTIFACT_IDENTITY`

Checkpoint:

- adapter readiness: `BLOCKED_BY_PENDING_WRITES`
- mapping readiness: `BLOCKED_BY_RUN_THREAD_MAPPING`
- async readiness: `OUT_OF_INITIAL_SCOPE`

Control plane:

- projection readiness: `BLOCKED_BY_CONTROL_PLANE_SCHEMA`

True resume:

- not approved

The durable backend layer is complete, but execution persistence orchestration still needs explicit ownership, adapter semantics, and safe projection contracts before any production write wiring is added.
