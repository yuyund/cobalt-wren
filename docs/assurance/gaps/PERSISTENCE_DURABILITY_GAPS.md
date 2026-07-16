# Persistence Durability Gaps

This document ranks the remaining persistence gaps after the current code-first audit.

## P0

- none identified in the current in-memory persistence boundary

## P1

| Gap | Evidence | Why it matters | Risk |
| --- | --- | --- | --- |
| ArtifactStore protocol is still metadata-only | `src/langgraph_automation/api/stores.py`, `src/langgraph_automation/integrations/artifact/base.py`, `src/langgraph_automation/integrations/artifact/memory_store.py` | The first durable artifact backend is blocked until the protocol can carry body semantics. | High |
| No durable artifact backend | `src/langgraph_automation/integrations/artifact/memory_store.py`, `src/langgraph_automation/apps/automation/services/runtime.py` | Artifact bodies are not restart-safe or deployment-shared. | High |
| No durable checkpoint backend | `src/langgraph_automation/integrations/checkpoint/memory_store.py`, `src/langgraph_automation/apps/automation/services/runtime.py` | Checkpoint bodies are not restart-safe or deployment-shared. | High |
| No body/metadata orchestration path | `src/langgraph_automation/apps/automation/services/execution.py`, `src/langgraph_automation/apps/automation/services/runs.py`, `src/langgraph_automation/graphs/runner.py` | The execution path does not write or verify artifact/checkpoint bodies today. | High |
| No idempotency / conflict protocol | `src/langgraph_automation/integrations/artifact/base.py`, `src/langgraph_automation/integrations/checkpoint/base.py` | Same identity / same content and same identity / different content are not distinguished. | High |
| No restart durability tests for stores | `tests/unit/artifact/test_memory_store.py`, `tests/unit/integrations/test_checkpoint_summary.py` | Current tests only prove process-local behavior. | High |
| No reconciliation path for orphan body / dangling metadata | current code has metadata-only models and EPHEMERAL stores | Crash windows and repair semantics are undefined. | High |

## P2

| Gap | Evidence | Why it matters | Risk |
| --- | --- | --- | --- |
| Missing checksum / serializer / version fields in store results | `src/langgraph_automation/integrations/artifact/base.py`, `src/langgraph_automation/integrations/checkpoint/base.py` | Integrity cannot be verified mechanically today. | Medium |
| Missing backend capability model | current protocol shapes are minimal | Future durable backends need a shared capability vocabulary for contract tests. | Medium |
| Durable backend orchestration remains unimplemented | `src/langgraph_automation/apps/automation/services/execution.py`, `src/langgraph_automation/apps/automation/services/runs.py`, `src/langgraph_automation/graphs/runner.py` | The execution path still does not write or verify artifact/checkpoint bodies. | Medium |
| FilesystemArtifactStore target design is deferred until protocol evolution | `docs/architecture/audit/ARTIFACT_STORE_PROTOCOL_SUFFICIENCY_AUDIT.md`, `docs/architecture/design/DURABLE_ARTIFACT_BACKEND_DESIGN.md` | The first durable artifact backend is a target design only until the protocol is evolved. | Medium |

## Current EPHEMERAL Limitations

- artifact bodies are process-local metadata objects only
- checkpoint bodies are process-local run-state dictionaries only
- restart destroys body state
- no shared-instance durability exists
- no conditional create or conflict protocol exists

## Recommended Closure Order

1. ArtifactStore protocol evolution
2. Durable artifact backend
3. Durable checkpoint backend
4. Orchestration integration with body-first / metadata-second writes
5. Restart durability tests
6. Reconciliation and cleanup policy

## Deferred Work

- durable artifact/checkpoint backend is deferred
- reconciliation worker is deferred
- cleanup command is deferred
- true resume is deferred
- run_workflow is deferred
- api.runtime is deferred
- persistence contract test harness is complete
- next block: durable artifact backend
- next block after that: Artifact Store Protocol Evolution Block V2

## Block Status

- production behavior was not changed
