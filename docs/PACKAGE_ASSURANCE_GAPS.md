# Package Assurance Gaps

This document records the mismatches found by the code-first audit.

## P0 Gaps

| Gap | Evidence | Why it matters | Risk |
| --- | --- | --- | --- |
| `apps/automation` is not yet fully free of package-internal imports | `src/langgraph_automation/apps/automation/services/runtime.py`, `workflow_config.py`, `execution.py`, `runs.py` still import `graphs.*` and `workflows.catalog` | The strongest package-completion claim is that application/control-plane code uses the package facade instead of package internals. The current code only routes the workflow-preparation bridge through `api.engine`; the broader control-plane package still depends on foundation internals. | P0 |
| Package-wide boundary guard for `apps/automation` is not present | The current guard covers only `src/langgraph_automation/apps/automation/services/workflow_preparation.py` | The repo does not yet mechanically prevent future `apps/automation` modules from importing `graphs.*`, `workflows.catalog`, or other internal package layers. | P0 |
| `docs/API_SURFACE.md` claims `UnknownWorkflowKindError` is implemented, but `api.workflow` does not export it | `src/langgraph_automation/api/workflow.py::__all__` omits it | This is a direct docs/code drift in the public surface description. | P0 |

## P1 Gaps

| Gap | Evidence | Why it matters | Risk |
| --- | --- | --- | --- |
| Explicit plugin auto-enable for validation is implied more than directly tested | `src/langgraph_automation/api/engine.py::create_engine` merges enabled plugins, but the tests currently prove runtime assembly for explicit plugins more clearly than validation-hook invocation | The intended contract is that explicit plugins are included in the effective plugin set, but there is no dedicated test that asserts a validation hook on an explicit plugin runs during `create_engine`. | P1 |
| `EnginePreparedWorkflow.graph` opacity is an API intent, not a structural guarantee | `src/langgraph_automation/api/engine.py::EnginePreparedWorkflow` stores `graph: object` | The current tests verify non-null and type identity, but they do not enforce a stronger non-inspection contract. | P1 |
| `workflows/applications` boundary is present but currently structural only | `tests/unit/architecture/test_application_workflow_public_api_boundary.py` | The directory is currently empty, so the guard has not yet been exercised against real application workflow files. | P1 |

## P2 Gaps

| Gap | Evidence | Why it matters | Risk |
| --- | --- | --- | --- |
| `docs/PACKAGE_COMPLETION.md` and related roadmap docs still describe future Package Complete+ work | Those files intentionally list deferred items | This is expected, but it can be misread as implementation debt if readers skip the audit docs. | P2 |
| The audit docs themselves are new and only lightly smoke-tested | `tests/unit/docs/test_package_assurance_audit_docs.py` | The docs structure is fixed, but the traceability tables are not deeply parsed by tests yet. | P2 |

## DOC_ONLY Claims

- `UnknownWorkflowKindError` is implemented in `api.workflow`.
- `Package Complete` is complete everywhere the docs currently imply it.
- `apps/automation` is fully facade-only.

## ASSUMED Behavior

- `EnginePreparedWorkflow.graph` should stay opaque to callers.
- Explicit plugins should continue to be auto-enabled for validation and runtime assembly.
- The current service bridge should remain thin until a later facade closure step.

## CONTRACT_DRIFT

- `docs/API_SURFACE.md` says `UnknownWorkflowKindError` is implemented, but the code does not export it.
- `docs/ARCHITECTURE.md` and `docs/CONTRACTS.md` describe an application/control-plane boundary that is stronger than what `apps/automation/services/runtime.py` and related service modules currently enforce.

## Untested or Under-tested Invariants

- package-wide `apps/automation` import restrictions
- explicit plugin validation-hook auto-enable behavior
- graph opacity as a strong caller contract

## Brittleness Risks

- architecture guards are file-specific in several places instead of package-wide
- audit docs can drift if the code changes and the traceability matrix is not refreshed
