# System Assurance Gaps

This document records the remaining code-first gaps after the system-wide audit.

Code is the source of truth.
Tests are the source of truth.
Docs are only design intent.
The supplemental report is hypothesis only.

## P0 Gaps

| Gap | Evidence | Why it matters | Risk |
| --- | --- | --- | --- |
| No open P0 gap remains after Block R | `src/langgraph_automation/apps/automation/services/runtime.py`, `execution.py`, and `runs.py` remain the exact control-plane execution adapters; `workflow_config.py` no longer imports graph internals; `tests/unit/architecture/test_apps_automation_package_boundary.py` enforces the exact allowlist; `docs/API_SURFACE.md` now treats unknown workflow kinds as `PluginResolutionError` | The previous P0 items were either removed, rerouted, or reclassified as an explicit execution-adapter boundary with exact guard coverage. | Low |

## P1 Gaps

| Gap | Evidence | Why it matters | Risk |
| --- | --- | --- | --- |
| Artifact/checkpoint bodies have no durable backend yet | `integrations/artifact/memory_store.py`, `integrations/checkpoint/memory_store.py` are in-memory only | The persistence boundary is safe but incomplete; durable artifact/checkpoint storage remains future work. | P1 |
| Django admin exposes control-plane models without explicit redaction policy | `src/langgraph_automation/apps/automation/admin.py` registers Workflow, Run, ExecutionSpan, RunEvent, Artifact, CheckpointMetadata with default `ModelAdmin` behavior | Privileged admin screens can surface raw model fields unless constrained separately. | P1 |
| `apps/automation` UI is redaction-aware, but the UI exposure matrix is not fully exercised against admin screens | `apps/automation/ui/builders.py` and `apps/web/views/*` are covered; admin is not | The dynamic UI path is safe, but the overall presentation surface includes more than the dynamic views. | P1 |
| Graph opacity is contractually intended rather than structurally enforced | `src/langgraph_automation/api/engine.py::EnginePreparedWorkflow` stores `graph: object` | Callers are expected not to inspect graph internals, but the current API cannot prevent it mechanically. | P1 |
| `workflows/applications` guard is currently structural only | `tests/unit/architecture/test_application_workflow_public_api_boundary.py`, `test_application_readiness_boundary.py` | The directory is empty today, so the guard has not been exercised against real application workflow modules. | P1 |

## P2 Gaps

| Gap | Evidence | Why it matters | Risk |
| --- | --- | --- | --- |
| Some dynamic UI template partials still contain TODO placeholders | `src/langgraph_automation/apps/web/templates/dynamic/partials/*`, `fields/*` | This is mostly presentation polish, but it can confuse future UI audits. | P2 |
| System assurance docs are new and still lightly smoke-tested | `tests/unit/docs/test_system_assurance_audit_docs.py` | The audit tables are present, but they are not deeply parsed. | P2 |
| Future plugin discovery, entry point discovery, and public run facade remain deferred | `docs/ROADMAP.md`, `docs/PACKAGE_COMPLETION.md`, `docs/PACKAGE_VERIFICATION_STRATEGY.md` | These are intentional deferrals, but they remain work items for later assurance blocks. | P2 |

## DOC_ONLY Claims

- The package facade and system boundary are fully finalized everywhere the docs imply.
- `workflows/applications` is ready for real application workflow code today.
- `apps/automation/services/runtime.py`, `execution.py`, and `runs.py` are the current control-plane execution adapter boundary.

## ASSUMED Behavior

- `EnginePreparedWorkflow.graph` will remain opaque to callers.
- The service bridge will remain thin and facade-routed.
- Existing safe-output and safe-error contracts will continue to hold when the control-plane evolves.

## CONTRACT_DRIFT

- No unknown-workflow-kind drift remains; unknown workflow kinds are represented by `PluginResolutionError` in the public surface.
- If a future `apps/automation` module imports package internals outside the exact execution-adapter allowlist, that would reintroduce boundary drift.

## Untested Or Under-tested Invariants

- package-wide `apps/automation` import restrictions beyond the exact execution-adapter allowlist
- admin exposure redaction
- durable artifact/checkpoint body persistence
- graph opacity as a caller contract

## Inherited Package Audit Gaps

The package audit baseline still informs this system audit:

- explicit plugin semantics remain a boundary that should be kept visible in tests
- package-facade verification is good, but only the facade path is guaranteed
- docs-only claims should not be promoted to guarantees without code and test evidence

## Recommended Next Assurance Blocks

### P0

1. None remaining; P0 issues were closed in Block R.

### P1

1. Persistence durability assurance
2. Admin/UI redaction assurance
3. Control-plane execution-path closure

### P2

1. Template polish and audit-doc refresh
