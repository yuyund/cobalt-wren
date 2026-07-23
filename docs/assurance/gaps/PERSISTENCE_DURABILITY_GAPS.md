> **Historical snapshot:** This audit records an earlier GraphRuntime-based architecture. The production graph package and control-plane graph path have been removed. Current behavior is defined by `docs/architecture/design/EXECUTION_LIFECYCLE_CONVERGENCE.md`.

# Persistence Durability Gaps

This document ranks the remaining persistence gaps after the current code-first audit.

## P0

- none identified in the current in-memory and filesystem persistence boundary

## Closed by X2

- implicit-vs-explicit artifact ambiguity is closed
- artifact logical identity ambiguity is closed
- retry identity ambiguity is closed
- slot/occurrence ambiguity is closed
- serialization ownership ambiguity is closed

## Closed by X2A

- internal/plugin boundary ambiguity is closed
- producer-controlled run_id ambiguity is closed
- attempt identity ambiguity is closed
- optional policy ambiguity is closed
- request equivalence ambiguity is closed
- validation bounds ambiguity is closed
- metadata boundedness ambiguity is closed
- deterministic write mapping ambiguity is closed

## P1

| Gap | Evidence | Why it matters | Risk |
| --- | --- | --- | --- |
| No body/metadata orchestration path | `src/langgraph_automation/apps/automation/services/execution.py`, `src/langgraph_automation/apps/automation/services/runs.py`, `src/langgraph_automation/graphs/runner.py` | The execution path does not write or verify artifact/checkpoint bodies today. | High |
| No reconciliation path for orphan body / dangling metadata | current code has metadata-only models and explicit pending recovery only | Crash windows and repair semantics are still bounded to the store layer. | High |
| No execution-owned persistence orchestration contract | `src/langgraph_automation/apps/automation/services/runtime.py`, `src/langgraph_automation/apps/automation/services/execution.py`, `src/langgraph_automation/apps/automation/services/runs.py` | `GraphRuntime` now receives selected stores through composition-bound run services, but execution ownership for artifact or checkpoint emission is still undefined. | High |

## P2

| Gap | Evidence | Why it matters | Risk |
| --- | --- | --- | --- |
| Durable body orchestration remains unimplemented | `src/langgraph_automation/apps/automation/services/execution.py`, `src/langgraph_automation/apps/automation/services/runs.py`, `src/langgraph_automation/graphs/runner.py` | The execution path still does not write or verify artifact/checkpoint bodies. | Medium |
| Missing durable checkpoint orchestration model | current control-plane wiring still stops at store construction | Future durable workflows still need a composition step that selects the checkpoint backend explicitly for persistence writes. | Medium |
| LangGraph adapter contract remains open | `venv/lib/python3.12/site-packages/langgraph/checkpoint/base/__init__.py`, `src/langgraph_automation/integrations/checkpoint/base.py` | Pending writes and config mapping are still unresolved at the framework boundary. | High |
| Control-plane projection schema remains incomplete | `src/langgraph_automation/apps/automation/models/artifact.py`, `src/langgraph_automation/apps/automation/models/checkpoint.py` | Safe durable references still do not have a dedicated projection schema for the new execution contract. | Medium |

## Current Limitations

- artifact bodies are process-local only in the default runtime wiring
- checkpoint bodies are process-local in the default runtime wiring, but the filesystem backend is now available for direct use
- physical persistence backend/root selection is owned by trusted package settings bound once at application composition, not workflow payload or run input
- deployment startup binding is owned by `AutomationConfig.ready()` and the trusted `LANGGRAPH_AUTOMATION` settings source
- deployment startup binding compares normalized binding signatures, not raw config text
- backend constructors run during runtime assembly, not during startup binding
- checkpoint metadata fidelity is lossless and defensively isolated in both current checkpoint backends
- execution persistence orchestration is still absent from the canonical production run path, even though selected stores now propagate into `GraphRuntime`
- normalized package config is not recomputed per run; bound run services reuse the same physical persistence policy across start / retry execution
- restart destroys the default in-memory checkpoint state

## Recommended Closure Order

1. Persistence orchestration contract for explicit emission and safe ownership
2. Restart durability tests under the selected checkpoint backend
3. Control-plane projection and reconciliation policy

## Deferred Work

- X2 artifact emission contract is complete
- checkpoint runtime selection is typed and canonical
- checkpoint runtime selection is complete
- checkpoint runtime selection is closed
- deployment startup binding is complete
- deployment startup fallback behavior is closed
- constructor timing ambiguity is closed
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
