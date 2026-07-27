# System Assurance Gaps

This document records the remaining code-first gaps after the system-wide audit.

Code is the source of truth.
Tests are the source of truth.
Docs are only design intent.
The supplemental report is hypothesis only.

## P0 Gaps

| Gap | Evidence | Why it matters | Risk |
| --- | --- | --- | --- |
| No open P0 gap remains after Block R | `src/cobalt_wren/apps/automation/services/runtime.py`, `execution.py`, and `runs.py` remain the exact control-plane execution adapters; the deleted workflow-config and graph adapters no longer form a control-plane dependency; `tests/unit/architecture/test_apps_automation_package_boundary.py` enforces a zero internal-import allowlist; `../../api/surface/API_SURFACE.md` treats unknown workflow kinds as `PluginResolutionError` | The previous P0 items were removed, rerouted, or reclassified as an explicit execution-adapter boundary with exact guard coverage. | Low |

## P1 Gaps

| Gap | Evidence | Why it matters | Risk |
| --- | --- | --- | --- |
| Artifact/checkpoint bodies still have no durable backend | `integrations/artifact/memory_store.py`, `integrations/checkpoint/memory_store.py` are in-memory only | The persistence boundary is now safe, but durable artifact/checkpoint storage remains future work. | P1 |
| Graph opacity remains a contract rather than a hard structural guarantee | `src/cobalt_wren/api/engine.py::EnginePreparedWorkflow` stores `graph: object` | Callers are expected not to inspect graph internals, but the API does not prevent it mechanically. | P1 |
| `workflows/applications` is still a structural guard with no implementation | `tests/unit/architecture/test_application_workflow_public_api_boundary.py`, `test_application_readiness_boundary.py` | The directory is empty today, so the guard has not been exercised against real application workflow modules. | P1 |

## Recently Closed In Block S

| Closed gap | Evidence | Why it matters |
| --- | --- | --- |
| Admin / dynamic UI redaction exposure | `src/cobalt_wren/apps/automation/admin.py`, `apps/automation/ui/*`, `apps/web/templates/*`, `tests/unit/apps/automation/test_admin_safety.py`, `tests/unit/apps/automation/test_ui_registry_safety.py`, `tests/unit/apps/web/test_dynamic_ui_safety.py` | Privileged and dynamic presentation paths now use explicit safe summary fields and negative tests instead of raw payload fields. |
| Observability metadata exposure | `src/cobalt_wren/integrations/observability/django_event_sink.py`, `tests/integration/django/test_event_sink.py` | Observability metadata is bounded, redacted, and checked against secret-like values. |
| Safe error exposure | `src/cobalt_wren/core/result_safety.py`, `tests/unit/core/test_result_safety.py`, `tests/unit/automation/test_run_safety.py` | Persisted errors now normalize to safe messages and strip traceback-like multiline input. |

## P2 Gaps

| Gap | Evidence | Why it matters | Risk |
| --- | --- | --- | --- |
| Some dynamic UI template partials still contain TODO placeholders | `src/cobalt_wren/apps/web/templates/dynamic/partials/*`, `fields/*` | This is presentation polish only, but it can distract future audits. | P2 |
| System assurance docs are still lightly smoke-tested | `tests/unit/docs/test_system_assurance_audit_docs.py` | The audit tables are present, but they are not deeply parsed. | P2 |
| Future plugin discovery, entry point discovery, and public run facade remain deferred | `../../roadmap/milestones/ROADMAP.md`, `../../package/completion/PACKAGE_COMPLETION.md`, `../../package/verification/PACKAGE_VERIFICATION_STRATEGY.md` | These are intentional deferrals, but they remain work items for later assurance blocks. | P2 |

## DOC_ONLY Claims

- The package facade and system boundary are fully finalized everywhere the docs imply.
- `workflows/applications` is ready for real application workflow code today.
- `apps/automation/services/runtime.py`, `execution.py`, and `runs.py` are the current control-plane execution adapter boundary.

## ASSUMED Behavior

- `EnginePreparedWorkflow.executable` remains opaque to callers.
- The service bridge will remain thin and facade-routed.
- Existing safe-output and safe-error contracts will continue to hold when the control-plane evolves.

## CONTRACT_DRIFT

- No unknown-workflow-kind drift remains; unknown workflow kinds are represented by `PluginResolutionError` in the public surface.
- If a future `apps/automation` module imports package internals outside the exact execution-adapter allowlist, that would reintroduce boundary drift.

## Untested Or Under-tested Invariants

- package-wide `apps/automation` import restrictions beyond the exact execution-adapter allowlist
- durable artifact/checkpoint body persistence
- graph opacity as a caller contract

## Recommended Next Assurance Blocks

### P1

1. Persistence durability assurance
2. Control-plane execution facade follow-up
3. Graph opacity hardening

### P2

1. Template polish and audit-doc refresh
2. Future application workflow readiness
