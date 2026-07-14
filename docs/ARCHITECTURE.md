# Architecture

## Layers

- `apps/automation`
- `graphs`
- `workflows`
- `workflows/reference`
- `workflows/applications`
- `workflows/catalog`
- `integrations`
- `core`
- `apps/web`

## Responsibilities

### apps/automation

- control plane
- Run lifecycle
- workflow config
- runtime assembly

### graphs

- execution foundation
- registry mechanism
- runtime
- runner
- builders
- instrumentation

### workflows/catalog

- built-in workflow definitions の composition

### workflows/reference

- diagnostic / smoke-test workflows

### workflows/applications

- future application workflows

### integrations

- external I/O boundary
- LLM / tool / artifact / checkpoint / observability

### core

- redaction / result safety / summary helpers

### apps/web

- UI layer

## Dependency Direction

- `apps/automation/services` may depend on `workflows/catalog`, `workflows/reference/*`, `graphs` registry/runtime types, and integration interfaces.
- `graphs` must not depend on workflows.
- `workflows` may use graphs public/foundation types.
- `workflows` must not depend on `apps/automation/services`.

## Forbidden Dependencies

- `graphs -> workflows/reference` forbidden
- `graphs -> workflows/applications` forbidden
- `graphs -> apps/automation/services` forbidden
- `graphs/builders.py -> concrete workflow import` forbidden
- `graphs/registry.py -> concrete workflow import` forbidden

- `workflows/reference -> apps/automation/services` forbidden
- `workflows/reference -> Django ORM` forbidden
- `workflows/reference -> concrete LiteLLMClient` forbidden
- `workflows/reference -> concrete EchoTool` forbidden

- workflow nodes -> Django settings forbidden
- workflow nodes -> provider raw object persistence forbidden
- workflow nodes -> raw `ToolResult.output` persistence forbidden

## Boundary Intent

The execution foundation owns reusable runtime mechanics.

Concrete workflow definitions live in workflow packages and are composed through `workflows/catalog`.

Reference workflows exist to verify wiring and safety.

Application workflows are future layers and should not be pulled into `graphs`.


## Configuration Boundary

- Config must not depend on internal module paths.
- Workflow structure belongs in plugin code.
- Workflow behavior parameters belong in config.
- Runtime assembly must use validated normalized config, not raw config sources.

## Public API Direction

- A future public facade is expected under `langgraph_automation.api.*`.
- Plugin authors should not depend on internal modules directly.
- `workflows/catalog.py` is package composition internal / semi-internal, not a public entry point.
- Internal graph vocabulary may remain in foundation code, but public-facing vocabulary should move toward workflow terms.
