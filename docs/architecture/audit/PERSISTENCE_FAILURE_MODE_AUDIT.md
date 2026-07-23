> **Historical snapshot:** This audit records an earlier GraphRuntime-based architecture. The production graph package and control-plane graph path have been removed. Current behavior is defined by `docs/architecture/design/EXECUTION_LIFECYCLE_CONVERGENCE.md`.

# Persistence Failure-Mode Audit

This audit records the current persistence paths, failure behavior, and missing durability guarantees.

## Actual Call Sites

Current code-first evidence shows:

- `src/langgraph_automation/apps/automation/services/runtime.py` constructs `MemoryArtifactStore` and `MemoryCheckpointStore`
- `src/langgraph_automation/runtime/assembly.py` threads store objects through `RuntimeDependencies`
- `src/langgraph_automation/graphs/runtime.py` carries the store objects on `GraphRuntime`
- `src/langgraph_automation/apps/automation/services/execution.py` dispatches graph execution with raw `Run.input_payload`
- `src/langgraph_automation/apps/automation/services/runs.py` normalizes run output/error for persistence
- `src/langgraph_automation/integrations/observability/django_event_sink.py` persists metadata rows for events, spans, artifacts, and checkpoints

No current code path in `src/` calls artifact or checkpoint store methods from the execution path.

Evidence:

- `rg -n "\\.put\\(|\\.save\\(|\\.load\\(|\\.delete\\(" src tests`
- `src/langgraph_automation/apps/automation/services/runtime.py`
- `src/langgraph_automation/apps/automation/services/execution.py`
- `src/langgraph_automation/apps/automation/services/runs.py`
- `src/langgraph_automation/graphs/runner.py`
- `src/langgraph_automation/integrations/observability/django_event_sink.py`

## Current Write / Read Flows

### Artifact

- current write: no execution-path write call exists
- current read: `MemoryArtifactStore.get()` and `list_for_run()` only in tests / direct use
- metadata write: `DjangoEventSink.artifact_created()` writes `Artifact` rows only
- metadata-body separation: body is not stored in Django
- target baseline remains body-first / metadata-second

### Checkpoint

- current write: no execution-path write call exists
- current read: `MemoryCheckpointStore.load()` only in tests / direct use
- metadata write: `DjangoEventSink.checkpoint_saved()` writes `CheckpointMetadata` rows only
- metadata-body separation: body is not stored in Django
- checkpoint metadata fidelity in the in-memory checkpoint boundary is lossless and defensively isolated
- target baseline remains body-first / metadata-second

## Failure-Mode Matrix

Buckets: W write failures, R read failures, C retry / concurrency failures, S safety failures, D restart / durability failures.

### Write failures

| ID | Failure mode | Current implementation behavior | Current tests | Target contract | Caller result | Metadata state | Body state | Retry safety | Recovery requirement | Observability behavior | Evidence level | Risk |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| W1 | input validation failure | blocked earlier by model/runtime validation, not store code | `tests/unit/automation/test_run_safety.py`, `tests/unit/automation/test_runtime_factory.py` | reject before persistence | safe failure | none | none | yes | fix input | safe error only | `TEST_CONFIRMED` | low |
| W2 | safety validation failure | redaction/safe-message helpers normalize output | `tests/unit/core/test_result_safety.py`, `tests/unit/automation/test_run_safety.py` | reject raw body / secret / traceback | safe failure | none | none | yes | fix data | safe error only | `TEST_CONFIRMED` | low |
| W3 | serialization failure | not exercised for body stores because no durable body serialization exists | none | fail before metadata commit | failure | none | none or partial | yes | implement durable serializer | safe error only | `GAP` | high |
| W4 | backend unavailable before write | no backend call in current execution path | none | fail before metadata commit | failure | none | none | yes | backend retry later | safe error only | `GAP` | high |
| W5 | partial body write | cannot occur in current in-memory-only wiring as a durable backend event | none | do not create metadata | failure | absent or partial body only | partial possible in future backend | yes if backend supports retry | repair / delete orphan body later | safe error only | `GAP` | high |
| W6 | body write timeout | not modeled today | none | fail safe | failure | none | unknown / partial possible in future | yes, if idempotent | retry or reconcile later | safe error only | `GAP` | high |
| W7 | body write succeeds / receipt verification fails | not modeled today | none | treat as failure and verify | failure | none | body may exist | maybe | reconciliation later | safe error only | `GAP` | high |
| W8 | body write succeeds / metadata transaction fails | not modeled today | none | avoid dangling metadata | failure | none | orphan body possible | yes | reconciliation later | safe error only | `GAP` | high |
| W9 | body write succeeds / metadata uniqueness conflict | current memory stores overwrite instead of conflict | `tests/unit/artifact/test_memory_store.py` | conflict on same identity / different content | current success with overwrite | overwritten | overwritten | no | add conflict detection later | safe error only | `CONTRACT_DRIFT` | high |
| W10 | observability emission fails after persistence | secondary failure is suppressed in observability paths | `tests/unit/graphs/test_runner.py`, `tests/unit/automation/test_run_failure_observability_masking.py` | primary persistence failure wins | primary preserved | unchanged | unchanged | yes | none for current path | suppressed secondary failure | `TEST_CONFIRMED` | low |

### Read failures

| ID | Failure mode | Current implementation behavior | Current tests | Target contract | Caller result | Metadata state | Body state | Retry safety | Recovery requirement | Observability behavior | Evidence level | Risk |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R1 | metadata missing | selectors return `None` for missing rows | selector tests and UI 404 tests | missing object is not materialized | 404 / none | absent | absent or unknown | yes | create or refresh metadata | safe not found | `CODE_CONFIRMED` | low |
| R2 | metadata exists / body missing | not currently detectable because no backend read path exists | none | fail loudly | failure | dangling | missing | yes if backend can recover | repair or delete metadata | safe error only | `GAP` | high |
| R3 | body read timeout | no body read path exists | none | retryable failure | failure | present | maybe present | yes | backend retry later | safe error only | `GAP` | high |
| R4 | body corrupted | no body read path exists | none | fail loudly | failure | present | corrupt | maybe | repair/delete later | safe error only | `GAP` | high |
| R5 | checksum mismatch | checksum not present in current result types | none | fail loudly | failure | present | mismatched | maybe | repair/delete later | safe error only | `GAP` | high |
| R6 | unsupported serializer/version | serializer/version not present in current result types | none | fail loudly | failure | present | unreadable | maybe | upgrade/migrate later | safe error only | `GAP` | high |
| R7 | backend credential/authorization failure | no durable backend credential path exists | none | fail safe | failure | none or unchanged | unchanged | maybe | fix credentials / permissions | safe error only | `GAP` | high |
| R8 | backend returns unexpected type | not modeled today | none | fail safe | failure | unchanged | unchanged | maybe | fix backend adapter | safe error only | `GAP` | medium |

### Retry / Concurrency failures

| ID | Failure mode | Current implementation behavior | Current tests | Target contract | Caller result | Metadata state | Body state | Retry safety | Recovery requirement | Observability behavior | Evidence level | Risk |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C1 | same write retried after timeout | no idempotent body write path exists | none | same identity + same content is idempotent | success or conflict depending on content | stable | stable | required | exact receipt verification | safe | `GAP` | high |
| C2 | same identity written concurrently | memory store last-wins | `tests/unit/artifact/test_memory_store.py` | conflict or compare-and-swap style guard | current overwrite | overwritten | overwritten | no | conditional create later | safe | `CONTRACT_DRIFT` | high |
| C3 | same identity / same content | not detected specially | none | idempotent success | success | unchanged | unchanged | required | none if matched | safe | `GAP` | medium |
| C4 | same identity / different content | memory store overwrites | `tests/unit/artifact/test_memory_store.py` | conflict | current overwrite | overwritten | overwritten | no | reject overwrite | safe | `CONTRACT_DRIFT` | high |
| C5 | metadata commit retried after body success | not modeled | none | idempotent or conflict-safe | failure or success | unchanged or duplicate | body may exist | required | dedupe / reconcile | safe | `GAP` | high |
| C6 | process crash between body write and metadata commit | not modeled because no durable body write path exists | none | orphan body possible, dangling metadata forbidden | failure on restart | none | orphan possible | retryable only with reconciliation | repair orphan later | safe | `GAP` | high |

### Safety failures

| ID | Failure mode | Current implementation behavior | Current tests | Target contract | Caller result | Metadata state | Body state | Retry safety | Recovery requirement | Observability behavior | Evidence level | Risk |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| S1 | secret-like value in metadata | observability sanitizes metadata; admin/UI render summaries | `tests/integration/django/test_event_sink.py`, `tests/unit/apps/automation/test_admin_safety.py`, `tests/unit/apps/web/test_dynamic_ui_safety.py` | no secret-like values in metadata rows | safe display | redacted / bounded | unchanged | yes | keep sanitizers in place | redacted | `TEST_CONFIRMED` | low |
| S2 | credential-bearing backend URL in metadata/log | runtime assembly keeps backend config in factory inputs, not metadata rows | `tests/unit/runtime/test_runtime_assembler_stores.py`, `tests/unit/automation/test_runtime_factory.py` | do not persist credentials | safe / hidden | none | unchanged | yes | keep credentials out of metadata | bounded | `CODE_CONFIRMED` | medium |
| S3 | raw traceback in persistence error | safe error helpers collapse multiline traceback-like input | `tests/unit/automation/test_run_safety.py`, `tests/unit/core/test_result_safety.py` | safe message only | safe failure | unchanged | unchanged | yes | none | safe message only | `TEST_CONFIRMED` | low |
| S4 | absolute local path exposed to UI/admin | redaction and summaries hide path-like values | `tests/unit/apps/automation/test_admin_safety.py`, `tests/unit/apps/web/test_dynamic_ui_safety.py` | path must not render | safe display | redacted / bounded | unchanged | yes | keep UI summaries | redacted | `TEST_CONFIRMED` | low |
| S5 | artifact/checkpoint body copied into Event metadata | current event sink stores metadata-only summaries, not body copies | `tests/integration/django/test_event_sink.py` | metadata only | safe display | bounded | body not copied | yes | keep body out of metadata | bounded | `TEST_CONFIRMED` | medium |
| S6 | body content included in safe error message | safe error helpers redact/truncate | `tests/unit/automation/test_run_safety.py`, `tests/unit/core/test_result_safety.py` | safe message only | safe failure | unchanged | unchanged | yes | none | safe message only | `TEST_CONFIRMED` | low |

### Restart / Durability failures

| ID | Failure mode | Current implementation behavior | Current tests | Target contract | Caller result | Metadata state | Body state | Retry safety | Recovery requirement | Observability behavior | Evidence level | Risk |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| D1 | process restart after successful write | in-memory stores lose state on restart | `tests/unit/integrations/test_checkpoint_summary.py`, `tests/unit/artifact/test_memory_store.py` | durable backend should survive restart | failure to read after restart | metadata may survive if stored separately | body lost | no | durable backend later | safe | `CODE_CONFIRMED` | high |
| D2 | process restart after body write before metadata commit | not modeled today | none | orphan body acceptable, dangling metadata forbidden | failure | none | orphan possible | yes with reconciliation | later cleanup | safe | `GAP` | high |
| D3 | backend state survives but application cache does not | no application cache layer exists for stores today | none | body store should remain authoritative | success if durable backend exists | metadata authoritative | body authoritative | yes | none if backend durable | safe | `GAP` | medium |
| D4 | metadata survives but backend storage is reset | current system can leave metadata referencing missing body only if a durable backend is later added and reset independently | none | read must fail loudly | failure | dangling | missing | yes if backend can heal | repair/delete metadata | safe error only | `GAP` | high |

## Current Gaps

- `MemoryArtifactStore` and `MemoryCheckpointStore` are process-local only
- there is no body read/write orchestration through the execution path
- no checksum, serializer, or version fields exist in the current store results
- no idempotency or conflict protocol exists
- no restart test exists for a durable backend
- no reconciliation path exists for orphan bodies or dangling metadata

## Evidence Summary

- `CODE_CONFIRMED`: `src/langgraph_automation/integrations/artifact/*`, `src/langgraph_automation/integrations/checkpoint/*`, `src/langgraph_automation/apps/automation/services/runtime.py`, `src/langgraph_automation/graphs/runtime.py`
- `TEST_CONFIRMED`: `tests/unit/artifact/*`, `tests/unit/integrations/test_checkpoint_summary.py`, `tests/unit/runtime/test_runtime_assembler_stores.py`, `tests/unit/automation/test_run_safety.py`, `tests/integration/django/test_event_sink.py`
- `GAP`: durable backend orchestration, checksum/versioning, restart durability, reconciliation
- `CONTRACT_DRIFT`: current overwrite semantics do not satisfy the target immutability/idempotency contract

## Deferred Work

- durable artifact/checkpoint backend is deferred
- true resume is deferred
- run_workflow is deferred
- api.runtime is deferred
- reconciliation worker is deferred

## Block Status

- production behavior was not changed
