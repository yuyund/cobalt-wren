# Package Test Roadmap

This roadmap prioritizes closure of the audit gaps.

## P0 Closure Order

### 1. Apps/Automation Boundary Closure

Purpose:

- enforce a package-wide boundary for `src/langgraph_automation/apps/automation/**/*.py`

Allowed changes:

- architecture guard tests
- small docs updates

Forbidden changes:

- runtime behavior
- public API changes
- service behavior changes

Target checks:

- forbid `graphs.*`, `workflows.catalog`, `plugins.registry`, `runtime.assembly`, `runtime.dependencies`, and `config.validator` imports from `apps/automation`

### 2. Public Surface Drift Closure

Purpose:

- align `docs/API_SURFACE.md` with the code surface

Allowed changes:

- docs updates
- minimal tests around public exports

Forbidden changes:

- new public API additions just to satisfy the docs

Target checks:

- resolve the `UnknownWorkflowKindError` mismatch

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

- `EnginePreparedWorkflow.graph` stays opaque in the facade-level tests

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
- external plugin discovery
- entry point discovery
- `company_agent`
- production application workflow
