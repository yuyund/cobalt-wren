# Package Assurance Gaps

This document records the mismatches found by the code-first audit.

## P0 Gaps

| Gap | Evidence | Why it matters | Risk |
| --- | --- | --- | --- |
| No open P0 gap remains after Block R | `src/cobalt_wren/apps/automation/services/runtime.py`, `execution.py`, and `runs.py` remain the exact control-plane execution adapters; the deleted workflow-config and graph adapters no longer form a control-plane dependency; `tests/unit/architecture/test_apps_automation_package_boundary.py` enforces a zero internal-import allowlist; `../../api/surface/API_SURFACE.md` now treats unknown workflow kinds as `PluginResolutionError` | The previous P0 items were either removed, rerouted, or reclassified as an explicit execution-adapter boundary with exact guard coverage. | Low |

## P1 Gaps

| Gap | Evidence | Why it matters | Risk |
| --- | --- | --- | --- |
| Explicit plugin auto-enable for validation is implied more than directly tested | `src/cobalt_wren/api/engine.py::create_engine` merges enabled plugins, but the tests currently prove runtime assembly for explicit plugins more clearly than validation-hook invocation | The intended contract is that explicit plugins are included in the effective plugin set, but there is no dedicated test that asserts a validation hook on an explicit plugin runs during `create_engine`. | P1 |
| `EnginePreparedWorkflow.executable` opacity is an API intent, not a structural guarantee | `src/cobalt_wren/api/engine.py::EnginePreparedWorkflow` stores `executable: object` | Tests verify execution behavior and object identity, but do not enforce a stronger non-inspection contract. | P1 |
| `workflows/applications` boundary is present but currently structural only | `tests/unit/architecture/test_application_workflow_public_api_boundary.py` | The directory is currently empty, so the guard has not yet been exercised against real application workflow files. | P1 |

## P2 Gaps

| Gap | Evidence | Why it matters | Risk |
| --- | --- | --- | --- |
| `PACKAGE_COMPLETION.md` and related roadmap docs still describe future Package Complete+ work | Those files intentionally list deferred items | This is expected, but it can be misread as implementation debt if readers skip the audit docs. | P2 |
| The audit docs themselves are new and only lightly smoke-tested | `tests/unit/docs/test_package_assurance_audit_docs.py` | The docs structure is fixed, but the traceability tables are not deeply parsed by tests yet. | P2 |

## DOC_ONLY Claims

- `Package Complete` is complete everywhere the docs currently imply it.
- `apps/automation/services/runtime.py`, `execution.py`, and `runs.py` are the current control-plane execution adapter boundary.
- `workflows/applications` is ready for real application workflow code today.

## ASSUMED Behavior

- `EnginePreparedWorkflow.executable` should stay opaque to callers.
- Explicit plugins should continue to be auto-enabled for validation and runtime assembly.
- The current service bridge should remain thin until a later facade closure step.

## CONTRACT_DRIFT

- No unknown-workflow-kind drift remains; unknown workflow kinds are represented by `PluginResolutionError` in the implemented public surface.
- If new `apps/automation` modules import package internals outside the exact execution-adapter allowlist, that would reintroduce boundary drift.

## Untested or Under-tested Invariants

- package-wide `apps/automation` import restrictions beyond the exact execution-adapter allowlist
- explicit plugin validation-hook auto-enable behavior
- graph opacity as a strong caller contract

## Brittleness Risks

- architecture guards are file-specific in several places instead of package-wide
- audit docs can drift if the code changes and the traceability matrix is not refreshed
