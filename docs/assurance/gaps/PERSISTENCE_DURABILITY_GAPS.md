# Persistence Durability Gaps

This document ranks the remaining persistence gaps after the current code-first audit.

## P0

- none identified in the current in-memory and filesystem persistence boundary

## P1

| Gap | Evidence | Why it matters | Risk |
| --- | --- | --- | --- |
| Checkpoint runtime selection is still deferred | `src/langgraph_automation/apps/automation/services/runtime.py`, `src/langgraph_automation/runtime/assembly.py` | The filesystem checkpoint backend exists, but the startup composition boundary still wires `MemoryCheckpointStore`. | High |
| No body/metadata orchestration path | `src/langgraph_automation/apps/automation/services/execution.py`, `src/langgraph_automation/apps/automation/services/runs.py`, `src/langgraph_automation/graphs/runner.py` | The execution path does not write or verify artifact/checkpoint bodies today. | High |
| No reconciliation path for orphan body / dangling metadata | current code has metadata-only models and explicit pending recovery only | Crash windows and repair semantics are still bounded to the store layer. | High |

## P2

| Gap | Evidence | Why it matters | Risk |
| --- | --- | --- | --- |
| Durable body orchestration remains unimplemented | `src/langgraph_automation/apps/automation/services/execution.py`, `src/langgraph_automation/apps/automation/services/runs.py`, `src/langgraph_automation/graphs/runner.py` | The execution path still does not write or verify artifact/checkpoint bodies. | Medium |
| Missing durable checkpoint orchestration model | current control-plane wiring still stops at store construction | Future durable workflows still need a composition step that selects the checkpoint backend explicitly. | Medium |

## Current Limitations

- artifact bodies are process-local only in the default runtime wiring
- checkpoint bodies are process-local in the default runtime wiring, but the filesystem backend is now available for direct use
- checkpoint metadata fidelity is lossless and defensively isolated in both current checkpoint backends
- restart destroys the default in-memory checkpoint state
- no deployment-wide default checkpoint durability exists yet

## Recommended Closure Order

1. Checkpoint runtime selection
2. Orchestration integration with body-first / metadata-second writes
3. Restart durability tests under the selected checkpoint backend
4. Reconciliation and cleanup policy

## Deferred Work

- checkpoint runtime selection remains deferred to W4
- checkpoint runtime selection is deferred
- reconciliation worker is deferred
- cleanup command is deferred
- true resume is deferred
- run_workflow is deferred
- api.runtime is deferred
- persistence contract test harness is complete
- runtime artifact backend selection is complete
- ArtifactStore protocol evolution is complete
- checkpoint protocol evolution is complete
- filesystem checkpoint backend implementation is complete

## Block Status

- production behavior was not changed
