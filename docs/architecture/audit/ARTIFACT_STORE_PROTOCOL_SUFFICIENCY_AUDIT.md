> **Historical snapshot:** This audit records an earlier GraphRuntime-based architecture. The production graph package and control-plane graph path have been removed. Current behavior is defined by `docs/architecture/design/EXECUTION_LIFECYCLE_CONVERGENCE.md`.

# Artifact Store Protocol Sufficiency Audit

This audit determines whether the current `ArtifactStore` protocol can support the first durable artifact backend.

Code is the source of truth.
Tests are the source of truth.
Docs record the current decision and the target backend boundary.

## Current Protocol Surface

The current public facade re-exports the artifact protocol from `src/langgraph_automation/api/stores.py`.

The current protocol is body-aware.

The protocol methods are:

- `put(request: ArtifactWriteRequest) -> StoredArtifact`
- `get(storage_key: str) -> ArtifactReadResult | None`
- `list_for_run(run_id: int | str) -> list[StoredArtifact]`

The request type is `ArtifactWriteRequest` with fields:

- `run_id`
- `storage_key`
- `body`
- `name`
- `kind`
- `content_type`
- `metadata`

The stored descriptor type is `StoredArtifact` with fields:

- `run_id`
- `storage_key`
- `name`
- `kind`
- `content_type`
- `size`
- `digest`
- `metadata`

The read result type is `ArtifactReadResult` with fields:

- `artifact`
- `body`

## Protocol Sufficiency Table

| Required semantic | Available in current protocol? | Exact type/field | Implementation evidence | Test evidence | Blocker? |
| --- | --- | --- | --- | --- | --- |
| Artifact body input | Yes | `ArtifactWriteRequest.body` | `src/langgraph_automation/integrations/artifact/base.py` | `tests/unit/architecture/test_artifact_store_protocol_sufficiency.py` | No |
| Body output | Yes | `ArtifactReadResult.body` | `src/langgraph_automation/integrations/artifact/base.py` | `tests/unit/architecture/test_artifact_store_protocol_sufficiency.py` | No |
| Stable logical identity | Yes | `storage_key` | `src/langgraph_automation/integrations/artifact/base.py`, `src/langgraph_automation/integrations/artifact/memory_store.py` | `tests/unit/artifact/test_memory_store.py` | No |
| Run association | Yes | `run_id` | `src/langgraph_automation/integrations/artifact/base.py`, `src/langgraph_automation/integrations/artifact/memory_store.py` | `tests/contract/persistence/test_artifact_store_baseline_contract.py` | No |
| Storage reference | Yes | `storage_key` | `src/langgraph_automation/integrations/artifact/base.py`, `src/langgraph_automation/integrations/artifact/keys.py` | `tests/unit/artifact/test_keys.py` | No |
| Content type | Yes | `content_type` | `src/langgraph_automation/integrations/artifact/base.py` | `tests/unit/artifact/test_memory_store.py` | No |
| Body size | Yes | `StoredArtifact.size` | `src/langgraph_automation/integrations/artifact/base.py` | `tests/unit/artifact/test_memory_store.py` | No |
| Body digest | Yes | `StoredArtifact.digest` | `src/langgraph_automation/integrations/artifact/base.py` | `tests/unit/artifact/test_memory_store.py` | No |
| Safe metadata | Yes | `metadata` | `src/langgraph_automation/integrations/artifact/base.py`, `src/langgraph_automation/integrations/artifact/memory_store.py` | `tests/contract/persistence/test_artifact_store_baseline_contract.py` | No |
| Idempotency equivalence | Yes | request + descriptor + body | `src/langgraph_automation/integrations/artifact/memory_store.py` | `tests/unit/artifact/test_memory_store.py` | No |
| Conflict detection | Yes | same key + different canonical request | `src/langgraph_automation/integrations/artifact/memory_store.py` | `tests/unit/artifact/test_memory_store.py` | No |
| Integrity error representable | Yes | `ArtifactIntegrityError` | `src/langgraph_automation/api/errors.py` | `tests/support/persistence/contracts.py` | No |

## Current Production Call Sites

Current production code wires `MemoryArtifactStore` through runtime assembly, but no production execution path calls `put`, `get`, or `list_for_run`.

Evidence:

- `src/langgraph_automation/apps/automation/services/runtime.py`
- `src/langgraph_automation/runtime/assembly.py`
- `src/langgraph_automation/graphs/runtime.py`
- `src/langgraph_automation/graphs/runner.py`
- `src/langgraph_automation/apps/automation/services/execution.py`
- `src/langgraph_automation/apps/automation/services/runs.py`

## Runtime Selection Boundary

The protocol is now paired with typed runtime configuration:

- `stores.artifact` normalizes to `MemoryArtifactStoreSettings` when absent
- explicit `stores.artifact.backend = memory` selects memory-backed runtime composition
- explicit `stores.artifact.backend = filesystem` selects `FilesystemArtifactStore`
- runtime assembly constructs the artifact store once per runtime build
- filesystem initialization failures are runtime-initialization failures, not memory fallbacks

## Protocol Sufficiency Decision

Decision: `APPROVED_FOR_IMPLEMENTATION`

Reason:

- the protocol now carries actual bytes body input and output
- the protocol exposes a stored descriptor with size and digest
- the protocol can express immutable, idempotent, and conflict-aware semantics
- integrity failure is representable as a dedicated error type

## First Durable Backend Candidate

The first durable backend candidate is now implemented as a local filesystem backend:

- target name: `FilesystemArtifactStore`
- target durability: `PROCESS_DURABLE`
- deployment scope: single host, same filesystem root, multiple process instances on that host

The default backend remains memory-backed `MemoryArtifactStore`.

The protocol decision remains `APPROVED_FOR_IMPLEMENTATION`, and the backend implementation now exists.

## Protocol Evolution Options

| Option | Summary | Fit | Recommendation |
| --- | --- | --- | --- |
| A | Keep the current body-aware provisional protocol | Simple and aligned with the current code path | Yes |
| B | Introduce a second long-lived artifact protocol | Adds parallel surface area without value here | No |
| C | Revert to metadata-only artifact records | Loses durable backend sufficiency | No |

Recommended path: `A`

Reason:

- it keeps the public protocol small
- it preserves body plane and metadata plane separation
- it localizes the filesystem backend implementation boundary

## Deferred Work

- checkpoint durability is deferred
- body/metadata orchestration is deferred
- true resume is deferred
- application workflow is deferred
- company_agent is deferred
