# Design Principles

This document defines the review standard for package architecture and internal implementation boundaries.
It applies to public APIs, plugin-author contracts, package internals, concrete adapters, the control plane, and presentation code.

## Change Containment First

The primary design objective is to minimize the scope of future change.
A design may contain more code when that code creates a real replacement boundary, keeps unstable dependencies local, or prevents a package-wide migration.

Loose coupling applies inside the package as well as between package consumers and the package.
Config loading, structural parsing, normalization, semantic validation, plugin resolution, runtime assembly, execution, persistence, observability, UI projection, concrete adapters, and control-plane composition are separate responsibilities.
They must not be collapsed into one composition module or service merely because they participate in the same execution path.

A forwarding layer is not valuable by itself.
A boundary is justified when it owns policy, semantics, data ownership, dependency direction, or a concrete replacement point.

## Package Surface And Internal Structure

Treat these as separate stability domains:

- public package API used by package consumers
- plugin-author SPI used by workflow and integration authors
- package-internal contracts and orchestration
- concrete adapters for external libraries and infrastructure
- control-plane and renderer composition

A stable public facade must not freeze package-internal classes accidentally.
An internal protocol must not be promoted to public contract solely because one implementation currently uses it.
Concrete adapters may change without requiring workflow authors or package consumers to change.

## External Libraries Are Implementations, Not Architecture

Use external libraries for commodity mechanics when they satisfy the requirement.
Place them behind package-owned contracts, facades, or adapters when their types or lifecycle would otherwise leak across the package.

Do not reimplement a library feature merely to avoid a dependency.
Do not add a library merely to reduce line count.
Custom code must provide package-owned policy or semantics that cannot be obtained by placing the library behind an adapter.

Examples of package-owned concerns include safe exposure, tool authorization, artifact identity, workflow contribution semantics, error mapping, and primary-failure preservation.
Examples of commodity mechanics include generic schema parsing, blob transport, distributed tracing export, and database persistence engines when no package-specific behavior is required.

## Workflow Flexibility

This repository provides a workflow construction package, not the final business workflows.
Production workflows should normally be contributed outside the foundation package.

The package must allow workflows to choose:

- state shape
- node topology
- conditional routing
- subgraphs
- LLM usage or no LLM usage
- tool usage or no tool usage
- artifact emission or no artifact emission
- checkpoint usage or no checkpoint usage
- workflow-specific configuration

Adding a workflow must not require changes to the graph foundation, runtime assembly, control-plane services, or existing workflow implementations unless the workflow introduces a genuinely new package capability.
The package constrains safety and integration boundaries, not business topology.

## OSS-Neutral Integration

Framework neutrality is not achieved by flattening every workflow implementation to a minimal Run result. The generic execution adapter remains capability-based and does not identify or inspect a specific workflow OSS. Framework-specific integration helpers sit outside that adapter and use stable public hooks to preserve useful execution, observability, action, checkpoint, and presentation semantics.

The foundation understands canonical operational records, opaque integration identifiers, registered schemas, action descriptors, and renderer-neutral view specifications. It must not contain framework-name conditionals. Common control-plane semantics provide cross-framework search, correlation, policy, audit, and operations; versioned integration projections preserve details that do not belong in the canonical schema.

Integration code may ship with the package while target OSS distributions remain optional and are detected in the user environment. Supported integration metadata, compatibility ranges, maturity, capabilities, and limitations must be centrally declared. Explicit integration selection is a foundation concern; automatic inference and low-configuration authoring are convenience concerns.

## Dynamic UI

Backend and control-plane state must be projected through a safe UI specification before rendering.
The intended dependency direction is:

`Backend / Domain / Control Plane -> safe projection -> UI specification -> renderer`

`ModelUIConfig`, `FieldSpec`, `ListPageSpec`, `DetailPageSpec`, `RelatedSectionSpec`, and `ActionSpec` are presentation projection concepts, not an attempt to expose Django models automatically.

Dynamic UI requires explicit allowlists for fields, relations, and actions, plus redaction and safe summaries.
Raw payloads are forbidden.
Renderers must not inspect Django `_meta` directly or depend on private service maps.
Reusable UI specification, Django model/query adapters, control-plane registration, and rendering should remain separable so a future renderer does not require domain rewrites.

## Safety

The package owns the final exposure contract even when external libraries perform the underlying work.
Replacing a provider, store, tracing library, serializer, or renderer must not bypass:

- safe output and safe error boundaries
- secret redaction
- raw provider and tool-output restrictions
- checkpointable-state restrictions
- tool policy
- primary-failure preservation

Safety is not an adapter-specific feature and cannot be disabled by selecting another implementation.

## Persistence

Keep these concerns distinct:

- artifact logical identity and emission semantics
- checkpoint logical identity and version semantics
- physical body storage
- execution persistence orchestration
- LangGraph checkpoint and resume mechanics
- control-plane metadata projection

`ArtifactStore` and `CheckpointStore` are package-owned replacement contracts.
Filesystem, database, object-storage, or LangGraph saver implementations are concrete mechanisms behind those contracts or behind an explicitly separate execution-persistence boundary.

Memory persistence remains `EPHEMERAL` by default.
Explicit filesystem artifact and checkpoint backends provide `PROCESS_DURABLE` storage.
That storage durability does not prove execution persistence orchestration or true resume.

Before true resume is implemented, the ownership and convergence of package `CheckpointStore`, LangGraph `BaseCheckpointSaver`, pending writes, thread identity, checkpoint namespace, serializer, retry, time travel, and `CheckpointMetadata` must be designed explicitly.
The package checkpoint contract and LangGraph resume path must not evolve independently without a declared source of truth.

## Configuration

Configuration processing is a staged pipeline:

`source loading -> structural parsing -> normalization -> semantic validation -> plugin resolution -> secret resolution -> runtime construction`

Keep package config, workflow definition config, and run execution input separate.
A schema library may replace structural parsing internals, but its models and errors must be mapped behind package-owned config contracts and `ConfigError` semantics.
Plugin existence, enabled contribution resolution, secret policy, workflow requirements, safety policy, and runtime factory availability remain package semantics.

## Evidence Of Loose Coupling

Interface count is not evidence of loose coupling.
Use replacement and extension tests to prove boundaries.
Relevant evidence includes:

- adding an external workflow without modifying existing workflows, graph foundation, runtime assembly, or control-plane services
- replacing `LLMClient`, `ToolRegistry`, `ToolPolicy`, `ArtifactStore`, `CheckpointStore`, `EventSink`, or `SecretResolver` without changing workflow code
- preparing workflows through the public facade in a headless environment
- rendering a safe UI projection without Django model introspection in the renderer
- running reusable contract tests against multiple adapters

A boundary that cannot survive a realistic replacement or extension test is provisional, even when it has a protocol or facade.

## Review Rules

For every new abstraction or custom implementation, answer:

1. What future change does this localize?
2. Which consumer is protected from which concrete implementation?
3. Are there multiple implementations or an unstable dependency?
4. Could an external library be used behind an adapter instead?
5. Does the code own package policy or semantics, or only commodity mechanics?
6. Does it make a real workflow easier to add without foundation changes?
7. Is the contract smaller and more stable than its implementations?
8. Is there a replacement or extension test?
9. Does it preserve all safety invariants?
10. Can it be changed or removed later without a package-wide migration?

Reject or defer abstractions that only add forwarding, generalize one implementation's convenience, or have no real consumer.
Retain package-owned facades, policies, identities, contribution contracts, runtime dependency boundaries, UI projection contracts, and error-safety contracts when they localize genuine change.

### External Workflow Freedom

External workflows own their orchestration framework, state model, node layout, and executable object. The foundation supplies a small public build context and capability-based execution adapter. Internal runtime bundles, registries, graph types, Django models, and control-plane services must not cross this boundary.
