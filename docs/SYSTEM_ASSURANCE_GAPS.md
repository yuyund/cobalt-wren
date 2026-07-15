# System Assurance Gaps

This document records the remaining code-first gaps after the system-wide audit.

Code is the source of truth.
Tests are the source of truth.
Docs are only design intent.
The supplemental report is hypothesis only.

## P0 Gaps

| Gap | Evidence | Why it matters | Risk |
| --- | --- | --- | --- |
| Control-plane services still import graph/runtime internals directly | `src/langgraph_automation/apps/automation/services/runtime.py`, `execution.py`, `runs.py`, `workflow_config.py` import `graphs.*` and `workflows.catalog` | The desired end state is an application/control-plane boundary centered on `langgraph_automation.api.engine`. The control plane still contains direct foundation imports outside the workflow-preparation bridge. | P0 |
| Package-wide `apps/automation` import guard is still missing | Existing guard coverage is file-specific and currently centered on `services/workflow_preparation.py` and a few other paths, not the whole `src/langgraph_automation/apps/automation/**/*.py` tree | A new control-plane module could reintroduce package-internal coupling without being caught by the current guard pattern. | P0 |
| Public surface docs still drift from code on workflow error vocabulary | `docs/API_SURFACE.md` still says `UnknownWorkflowKindError` is implemented, but `src/langgraph_automation/api/workflow.py::__all__` does not export it | Public surface drift is a contract problem, not just a documentation typo. | P0 |
| Service layer runtime/execution remains on the direct graph path | `apps/automation/services/execution.py`, `runs.py`, `runtime.py` still dispatch through `graphs.runner` and `graphs.runtime` | The system still has a direct execution path outside the package facade. | P0 |

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

## ASSUMED Behavior

- `EnginePreparedWorkflow.graph` will remain opaque to callers.
- The service bridge will remain thin and facade-routed.
- Existing safe-output and safe-error contracts will continue to hold when the control-plane evolves.

## CONTRACT_DRIFT

- `docs/API_SURFACE.md` claims `UnknownWorkflowKindError` is implemented, but `api.workflow` does not export it.

## Untested Or Under-tested Invariants

- package-wide `apps/automation` import restrictions
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

1. Control-plane boundary closure
2. Public surface drift closure

### P1

3. Persistence durability assurance
4. Admin/UI redaction assurance
5. Control-plane execution-path closure

### P2

6. Template polish and audit-doc refresh
