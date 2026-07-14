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
