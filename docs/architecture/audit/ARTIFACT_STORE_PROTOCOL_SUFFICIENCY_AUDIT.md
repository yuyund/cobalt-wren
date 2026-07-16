# Artifact Store Protocol Sufficiency Audit

This audit determines whether the current `ArtifactStore` protocol can support a durable artifact backend.

Code is the source of truth.
Tests are the source of truth.
Docs record the current decision and the target backend boundary.

## Current Protocol Surface

The current public facade re-exports the artifact protocol from `src/langgraph_automation/api/stores.py`.

The current protocol is metadata-only.

The protocol methods are:

- `put(artifact: ArtifactWriteResult) -> ArtifactWriteResult`
- `get(artifact_id: str) -> ArtifactWriteResult | None`
- `list_for_run(run_id: int) -> list[ArtifactWriteResult]`

The value type is `ArtifactWriteResult` with fields:

- `storage_key`
- `name`
- `kind`
- `content_type`
- `size`
- `metadata`

There is no body field.
There is no body-bearing request type.
There is no body-bearing read result type.

## Protocol Sufficiency Table

| Required semantic | Available in current protocol? | Exact type/field | Implementation evidence | Test evidence | Blocker? |
| --- | --- | --- | --- | --- | --- |
| Artifact body input | No | none; `put()` accepts `ArtifactWriteResult` only | `src/langgraph_automation/integrations/artifact/base.py` | `tests/unit/architecture/test_artifact_store_protocol_sufficiency.py` | Yes |
| Body output | No | `get()` returns `ArtifactWriteResult | None` only | `src/langgraph_automation/integrations/artifact/base.py` | `tests/unit/architecture/test_artifact_store_protocol_sufficiency.py` | Yes |
| Stable logical identity | Partial | `storage_key` | `src/langgraph_automation/integrations/artifact/base.py`, `src/langgraph_automation/integrations/artifact/memory_store.py` | `tests/unit/artifact/test_memory_store.py` | Yes, because identity is reference-only |
| Run association | Partial | `metadata['run_id']` by convention | `src/langgraph_automation/integrations/artifact/memory_store.py` | `tests/contract/persistence/test_artifact_store_baseline_contract.py` | Yes, because it is convention only |
| Storage reference | Yes | `storage_key` | `src/langgraph_automation/integrations/artifact/base.py`, `src/langgraph_automation/integrations/artifact/keys.py` | `tests/unit/artifact/test_keys.py` | No |
| Content type | Yes | `content_type` | `src/langgraph_automation/integrations/artifact/base.py` | `tests/unit/artifact/test_memory_store.py` | No |
| Body size | Yes, but metadata-only | `size` | `src/langgraph_automation/integrations/artifact/base.py` | `tests/unit/artifact/test_memory_store.py` | Yes for durable body semantics |
| Safe metadata | Yes | `metadata` | `src/langgraph_automation/integrations/artifact/base.py`, `src/langgraph_automation/integrations/artifact/memory_store.py` | `tests/contract/persistence/test_artifact_store_baseline_contract.py` | No |
| Idempotency判定に必要な情報 | No | no digest/checksum/body identity | `src/langgraph_automation/integrations/artifact/base.py` | `tests/unit/architecture/test_artifact_store_protocol_sufficiency.py` | Yes |
| Integrity判定に必要な情報 | No | no checksum / serializer / schema version | `src/langgraph_automation/integrations/artifact/base.py` | `tests/unit/architecture/test_artifact_store_protocol_sufficiency.py` | Yes |

## Current Production Call Sites

Current production code wires `MemoryArtifactStore` through runtime assembly, but no production execution path calls `put`, `get`, or `list_for_run`.

Evidence:

- `src/langgraph_automation/apps/automation/services/runtime.py`
- `src/langgraph_automation/runtime/assembly.py`
- `src/langgraph_automation/graphs/runtime.py`
- `src/langgraph_automation/graphs/runner.py`
- `src/langgraph_automation/apps/automation/services/execution.py`
- `src/langgraph_automation/apps/automation/services/runs.py`

## Protocol Sufficiency Decision

Decision: `BLOCKED_BY_PROTOCOL`

Reason:

- the current protocol can move metadata-like records, but it cannot carry actual artifact body input or output
- the current protocol cannot express durable body integrity, immutability, or idempotent retry semantics
- the current protocol cannot distinguish same-content retry from different-content conflict

## First Durable Backend Candidate

The first durable backend candidate remains a local filesystem backend:

- target name: `FilesystemArtifactStore`
- target durability: `PROCESS_DURABLE`
- deployment scope: single host, same filesystem root, multiple process instances on that host

The default backend remains MemoryArtifactStore.

This remains a target design only. It is not implementable under the current protocol without protocol evolution.

The backend design therefore remains blocked by current protocol sufficiency.

## Protocol Evolution Options

| Option | Summary | Fit | Recommendation |
| --- | --- | --- | --- |
| A | Add body to the current public artifact value type | Simple but expands the public facade immediately | No |
| B | Introduce internal/provisional body-bearing request/result types | Keeps the public protocol stable while enabling durable body I/O | Yes |
| C | Split body producer/consumer into a separate internal boundary | Safe, but still needs an internal body-bearing seam | Secondary |
| D | Only model external pre-existing body references | Insufficient for the first durable backend | No |

Recommended path: `B`

Reason:

- it keeps the current public facade stable
- it gives the durable backend an explicit body-bearing seam
- it localizes protocol evolution before backend implementation

## Deferred Work

- durable artifact backend implementation is deferred
- protocol evolution block is deferred
- checkpoint durability is deferred
- body/metadata orchestration is deferred
- true resume is deferred
- application workflow is deferred
- company_agent is deferred
