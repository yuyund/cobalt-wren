# ADR 0001: Canonical, Semantic, and Integration-Native Observation Layers

- Status: Accepted
- Date: 2026-07-27

## Context

Cobalt Wren operates workflows implemented with ordinary Python and optional
workflow frameworks. Framework neutrality must not erase information that is
specific to a framework, nor should framework runtime objects leak into the
stable control-plane contract.

## Decision

Observation data is separated into three layers.

### 1. Canonical facts

Framework-independent operational facts used for search, audit, authorization,
aggregation, and the default UI. Examples include runs, execution spans, events,
artifacts, checkpoint references, and actions.

Canonical models must not contain framework checkpoint objects, compiled graph
objects, provider SDK responses, framework state containers, or other private
runtime objects.

### 2. Semantic projections

Versioned, framework-independent meanings projected from integration-specific
observations. Semantic projections provide stable UI contracts without claiming
that different framework execution models are identical.

Initial schema scope:

- `semantic.execution_unit.lifecycle.v1`
- `semantic.state.snapshot.v1`
- `semantic.route.decision.v1`
- `semantic.interaction.lifecycle.v1`
- `observability.coverage.v1`

A semantic projection is introduced only when an existing canonical fact cannot
represent the meaning without integration-specific heuristics or duplicated
persistence.

### 3. Integration-native projections

Append-only, bounded, redacted, versioned integration detail stored through
`IntegrationProjectionRecord`. Examples include:

- `langgraph.checkpoint_ref.v1`
- `langgraph.task.v1`
- `llamaindex.step.v1`
- `native.step.v1`

Unknown schemas remain storable and render through a safe generic structured
view. Known schemas may register specialized renderers.

## Boundaries

- Workflow adapters observe node, step, state, route, and checkpoint semantics.
- LLM adapters observe prompts, responses, model information, and usage.
- Tool adapters observe arguments, results, duration, and policy decisions.
- Artifact adapters observe object metadata and storage references.
- Raw state is not a canonical model and is not retained by default.
- Safe projections use the shared bounded, redacted summary primitives.
- Diagnostic payloads are permission-controlled and retention-bounded.
- Framework private APIs are avoided. Any exception must be isolated, documented,
  version-gated, and covered by compatibility tests.

## Capabilities and coverage

Integration capability declarations describe static support. Run-level
observation coverage separately records whether data was observed, absent,
unsupported, not applicable, or lost because instrumentation failed. An empty UI
must not imply that an operation did not occur when it was merely unobservable.

## Deferred work

The following are intentionally deferred until their contracts are proven in
one integration:

- public `normalize_event(object)` APIs
- runtime-object-based state inspection
- generic structural state diffing
- complete graph descriptors
- broad specialized renderer registries

## Consequences

Adding an integration should normally not require a canonical schema change.
The common UI can remain stable while integration-native details retain
framework fidelity and schema versions absorb framework-version differences.
