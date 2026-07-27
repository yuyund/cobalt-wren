# Package Test Roadmap

This roadmap prioritizes closure of the audit gaps.

Status update:

- the P0 boundary and public-surface drift items were closed in System P0 Assurance Gap Closure Block R
- the remaining roadmap now focuses on P1 and P2 assurance hardening

## P0 Closure Order

### 1. Apps/Automation Boundary Closure

Purpose:

- enforce a package-wide boundary for `src/cobalt_wren/apps/automation/**/*.py`

Allowed changes:

- architecture guard tests
- small docs updates

Forbidden changes:

- runtime behavior
- public API changes
- service behavior changes

Target checks:

- forbid new `graphs.*`, `workflows.catalog`, `plugins.registry`, `runtime.assembly`, `runtime.dependencies`, and `config.validator` imports from `apps/automation`
- allow only exact execution-adapter paths for the current control-plane execution boundary

### 2. Public Surface Drift Closure

Purpose:

- align `../../api/surface/API_SURFACE.md` with the code surface

Allowed changes:

- docs updates
- minimal tests around public exports

Forbidden changes:

- new public API additions just to satisfy the docs

Target checks:

- resolve the unknown-workflow-kind mismatch by treating `PluginResolutionError` as the canonical unknown workflow error

### 3. Explicit Plugin Assurance

Purpose:

- prove explicit plugins are auto-enabled for validation as well as runtime assembly

Allowed changes:

- unit or integration tests only

Forbidden changes:

- engine behavior changes unless the audit finds a true bug

Target checks:

- explicit plugin validation hook is invoked when expected
- duplicate explicit plugin resolution still fails safely

## P1 Closure Order

### 4. Graph Opaqueness Assurance

Purpose:

- prove callers do not depend on graph internals

Allowed changes:

- tests only

Forbidden changes:

- changing the public return type

Target checks:

- `EnginePreparedWorkflow.executable` stays opaque in facade-level tests

### 5. Service Bridge Boundary Regression

Purpose:

- keep `apps/automation/services/workflow_preparation.py` routed through `api.engine`

Allowed changes:

- boundary guards
- service integration regression tests

Forbidden changes:

- reintroducing direct package-internal imports

Target checks:

- service bridge continues to avoid `workflows.prepare`, `workflows.catalog`, `plugins.registry`, and runtime/config internals

### 6. Control-Plane Execution Adapter Boundary

Purpose:

- document and guard the remaining direct graph/runtime imports that are part of the current execution adapter

Allowed changes:

- exact allowlist updates for `apps/automation/services/runtime.py`, `execution.py`, and `runs.py`
- docs updates that explain the direct execution adapter boundary

Forbidden changes:

- spreading graph/runtime imports into new `apps/automation` modules
- introducing new direct package-internal dependencies without an explicit execution-adapter rationale

Target checks:

- exact allowlist remains limited to the current execution adapter modules
- deleted graph/config adapters remain absent from the control-plane path

## P2 Closure Order

### 6. Audit Docs Parsing

Purpose:

- make the audit docs easier to verify mechanically

Allowed changes:

- docs tests

Forbidden changes:

- behavior changes

Target checks:

- traceability matrix and gap sections remain present

## Future / Deferred Blocks

- `run_workflow`
- `api.runtime`
- graph execution public API
- worker / queue / outbox
- true resume
- plugin API version migration
- broken-plugin partial-startup policy
- `company_agent`
- production application workflow
