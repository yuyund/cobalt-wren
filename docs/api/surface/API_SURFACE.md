# API Surface

This document defines the boundary between public, provisional, internal, config-facing, and future APIs for `cobalt-wren`.

The goal is to keep the package small on the outside, flexible on the inside, and safe for future plugin authors who should not depend on internal implementation details.

## API stability levels

- `Public`: stable surface that external plugin authors and application workflows may import.
- `Provisional`: likely future public surface, but still subject to change.
- `Internal`: package implementation detail; do not import from outside the package.
- `Config-facing`: concepts that are controlled through config, not by arbitrary Python imports.
- `Future`: directionally planned, but not implemented yet.

## Public API principles

The package-wide design and review rules are defined in `../../architecture/design/DESIGN_PRINCIPLES.md`. Public API stability, plugin-author SPI, internal orchestration, concrete adapters, and control-plane rendering are separate stability domains.

- Keep the public API narrow.
- Expose public APIs through facades, not by encouraging deep imports.
- Plugin authors should not import internal modules directly.
- Public vocabulary should prefer `workflow` where user-facing terms are needed.
- Internal implementation may continue to use `graph` vocabulary.
- Config may adjust behavior, but it must not allow arbitrary imports or safety bypasses.

## Public module layout

Current implemented public facade:

- `cobalt_wren.api.llm`
- `cobalt_wren.api.tools`
- `cobalt_wren.api.stores`
- `cobalt_wren.api.events`
- `cobalt_wren.api.errors`
- `cobalt_wren.api.plugins`
- `cobalt_wren.api.workflow`
- `cobalt_wren.api.engine`

Deferred public surfaces:

- `cobalt_wren.api.runtime`

Package P0-B plus the package facade blocks implement the minimal facade described below.

## Workflow API surface

Current internal foundation names remain graph-oriented:


Implemented public workflow vocabulary:

- `WorkflowDefinition`
- `WorkflowRequirements`

Decisions:

- `api.workflow` exposes `WorkflowDefinition` directly.
- `workflows/catalog.py` is package composition, not a public API surface.
- Plugin authors should move toward a future registration API rather than editing catalog internals directly.

Unknown workflow kinds are surfaced through `PluginResolutionError`.

## Runtime API surface

Current candidates:


Internal composition helpers:

- `ApplicationRuntimeFactory`
- `RunExecutionServices`

Guidance:

- A future `WorkflowRuntime` protocol or facade may replace direct reliance on the concrete class.
- `ApplicationRuntimeFactory` and `RunExecutionServices` remain internal composition helpers and are not exported through the public facade.
- deployment-owned startup config sources such as `COBALT_WREN` and `AutomationConfig.ready()` are configuration/bootstrap concerns, not public API surface.

## Tool API surface

Current candidates:

- `ToolRegistry`
- `ToolPolicy`
- `ToolPolicyContext`
- `ToolPolicyDecision`
- `ToolResult`

Future concepts:

- `ToolDefinition`
- `ToolPlugin`
- tool input/output schema
- permission metadata
- safety metadata

Guidance:

- Tools must always be mediated through policy.
- Default deny must remain the baseline.
- Raw `ToolResult.output` must not flow directly into state, output, or events.
- Shell, file, and network tools are out of scope for now.

## LLM API surface

Current candidates:

- `LLMClient`
- `LLMRequest`
- `LLMResult`

`LLMRequest` is intentionally a loose, provisional request-shape alias. It should not be narrowed to a provider-specific message schema.

Internal-only handling:

- concrete `LiteLLMClient`
- provider-specific raw payload handling
- settings / env secret resolution
- request-shape narrowing to a single provider format

Guidance:

- Workflow nodes should not import concrete providers.
- `LLMResult.raw` must not be stored in state, output, or events.
- Provider raw objects must not cross the safe boundary.

## Store API surface

Current candidates:

- `ArtifactStore`
- `ArtifactWriteRequest`
- `StoredArtifact`
- `ArtifactReadResult`
- `CheckpointStore`
- `CheckpointWriteRequest`
- `StoredCheckpoint`
- `CheckpointReadResult`

Internal / provisional concepts:

- `ArtifactEmissionRequest`
- `ArtifactIdentity`
- `ArtifactSlot`
- `ArtifactOccurrence`
- `ArtifactEmitter`
- `ArtifactStorePlugin`
- `CheckpointStorePlugin`
- `ArtifactEmissionCollector`
- `ArtifactPersistenceOrchestrator`
- `LocalFileArtifactStore`
- `S3ArtifactStore`
- persistent checkpoint backend

Guidance:

- Persistent stores are still provisional, but `ArtifactStore` now has a body-aware breaking revision that supports immutable/idempotent/conflict-aware writes.
- `ArtifactWriteRequest` owns caller serialization.
- `StoredArtifact` is the normalized descriptor returned from `put()`.
- `ArtifactReadResult` returns descriptor plus body from `get()`.
- `ArtifactEmissionRequest` is the explicit package-internal emission contract and remains store-independent.
- `ArtifactIdentity` is logical identity only and does not imply a storage location.
- `ArtifactSlot` and `ArtifactOccurrence` are caller-issued logical discriminators.
- `ArtifactEmitter` remains package-internal until a future orchestration layer is approved.
- external plugin import of `cobalt_wren.integrations.artifact.emission` is unsupported
- `ArtifactEmissionContext` owns the execution-provided `run_id`
- attempt identifiers are excluded from the default identity and storage encoding
- explicit emission is required-only in X2A; optional / best-effort modes are deferred
- `api.stores` remains the minimal public store facade.
- `FilesystemArtifactStore` is the first durable backend, but it is not exported from `api.stores`.
- artifact runtime selection is controlled by typed config under `stores.artifact` in trusted package settings
- `MemoryArtifactStore` remains the default when the section is absent
- `FilesystemArtifactStore` is explicit opt-in and must fail startup on initialization errors
- the filesystem root is trusted configuration and must not be echoed in runtime diagnostics
- Storage keys and file paths must remain redaction-safe.
- Absolute local file paths must not appear in UI or API output.
- `CheckpointStore` is now a versioned append-only checkpoint repository contract.
- `CheckpointWriteRequest` owns caller serialization.
- `StoredCheckpoint` is the normalized descriptor returned from `save()`.
- `CheckpointReadResult` returns descriptor plus body from `load_latest()` / `load_checkpoint()`.
- `CheckpointStore` uses caller-issued checkpoint IDs, store-assigned revisions, and linear parent/head preconditions.
- accepted checkpoint metadata is preserved as a lossless logical JSON value and is not redacted on persistence
- returned checkpoint metadata is defensively isolated from stored state
- `CheckpointStore` is approved for durable backend implementation.
- `CheckpointStore` is storage-only; execution persistence orchestration and LangGraph saver integration remain future internal layers.
- PROCESS_DURABLE checkpoint storage does not imply true resume. Package checkpoint semantics and LangGraph `BaseCheckpointSaver` semantics require an explicit convergence design before a public resume surface is added.
- FilesystemCheckpointStore is implemented in `cobalt_wren.integrations.checkpoint`.
- It remains internal/provisional and is not re-exported from `api.stores`.
- checkpoint runtime selection is controlled by typed config under `stores.checkpoint` in trusted package settings.
- `MemoryCheckpointStore` remains the default checkpoint backend when the section is absent.
- `FilesystemCheckpointStore` is explicit opt-in and must fail startup on initialization errors.
- `build_checkpoint_store()` is the canonical construction point, and `api.stores` remains the minimal public facade.
- `api.runtime` remains deferred.
- no public execution persistence facade is exposed yet.

## Observability API surface

Current candidate:

- `EventSink`

Provisional:

- span / event metadata schema

Future:

- `EventSinkPlugin`
- OpenTelemetry sink
- Langfuse sink

Guidance:

- EventSink failures must not overwrite the primary failure.
- Metadata must be redacted and bounded.
- Full prompt, raw response, and raw tool output must not enter event metadata.

## Errors API surface

Implemented:

- `cobalt_wren.api.errors`

Exports:

- `FrameworkError`
- `ConfigError`
- `PluginRegistrationError`
- `PluginResolutionError`
- `PluginValidationError`
- `RuntimeAssemblyError`
- `SafetyBoundaryError`

The full error taxonomy remains documented in `../../contracts/errors/ERROR_TAXONOMY.md`, and the staging policy remains in `../errors/API_ERRORS_FACADE.md`.

Future public candidates may include:

- `WorkflowConfigurationError`
- `RuntimeDependencyError`
- `ToolPolicyDeniedError`
- `ProviderError`
- `ExecutionError`

Current guidance:

- Do not rename internal graph error classes now.
- A future public facade may map graph vocabulary to workflow vocabulary.
- No additional error classes are exported beyond the minimal facade.
- The minimal public error facade is intentionally smaller than the full taxonomy.
- `FrameworkError`, `ConfigError`, `PluginRegistrationError`, `PluginResolutionError`, `PluginValidationError`, `RuntimeAssemblyError`, and `SafetyBoundaryError` were the minimal candidates and are now implemented.
Unknown workflow kinds remain represented by `PluginResolutionError` in the implemented public surface.

## Plugin API surface

Implemented:

- `cobalt_wren.api.plugins`

Exports:

- `Plugin`
- `PluginMetadata`
- `PluginContributions`
- `ToolContribution`
- `ProviderContribution`
- `StoreContribution`
- `EventSinkContribution`

Not exported:

- `PluginRegistry`
- `WorkerContribution`
- `UIContribution`
- `ValidationContext`
- `FactoryContext`
- `SecretResolver`

Guidance:

- `api.plugins` is the public vocabulary for plugin packages and contributions.
- `PluginContributions.workflows` aggregates workflow contributions, but `WorkflowContribution` itself is owned by `api.workflow`.
- `PluginRegistry` remains an internal mechanism under `cobalt_wren.plugins.registry`.
- `api.plugins` does not expose registry, config validator, runtime assembly, or concrete runtime dependencies.

## Implemented public facade in P0-B

- `cobalt_wren.api.llm`
- `cobalt_wren.api.tools`
- `cobalt_wren.api.stores`
- `cobalt_wren.api.events`
- `cobalt_wren.api.workflow`
- `cobalt_wren.api.engine`

These modules re-export selected stable interfaces only. They do not expose runtime concrete implementation, plugin loader, config loader, or public error taxonomy.

`api.stores` is a provisional breaking revision for the artifact surface, not a stable storage API.
It is a body-aware breaking revision that keeps the public facade minimal while exposing `ArtifactWriteRequest`, `StoredArtifact`, and `ArtifactReadResult`.

## Deferred public surfaces

- `cobalt_wren.api.runtime`
- `WorkflowPlugin`
- `ToolPlugin`
- plugin loader
- config loader

## Internal-only modules

The following should be treated as internal-only for plugin authors and external consumers:

- `cobalt_wren.apps.automation.services.*`
- `cobalt_wren.apps.automation.models`
- `cobalt_wren.workflows.catalog`
- `cobalt_wren.core.result_safety`
- `cobalt_wren.core.redaction`
- concrete integration modules
- Django settings and model internals

Notes:

- `workflows/catalog.py` is package composition internal / semi-internal.
- The built-in workflow catalog is currently empty. Native examples live under `examples/native/` and require explicit plugin registration.
- A future registration API should become the supported path for extending workflows.

## Plugin taxonomy

- Plugin taxonomy is defined in `../../plugins/PLUGINS.md`.
- Plugins should depend on `cobalt_wren.api.*` public facade modules, not internal implementation modules.
- `api.workflow` and `api.errors` are implemented public facades, `api.engine` is the public-facing provisional package facade, and `api.runtime` remains deferred.
- Manual registration and registry boundaries are defined in `../../plugins/PLUGIN_REGISTRATION.md`.
- Plugin API shapes are documented in `../../plugins/PLUGIN_API_SHAPE.md`.
- Plugin API facade staging is defined in `../../plugins/PLUGIN_API_FACADE.md`.

## Workflow facade staging

- `api.workflow` is implemented and defines `WorkflowMetadata`, `WorkflowRequirements`, `WorkflowDefinition`, and `WorkflowContribution`.
- `api.plugins` aggregates workflow contributions through `PluginContributions.workflows`.
- `api.engine` is implemented as the public-facing provisional package facade.
- Built-in workflow wiring uses `workflows.catalog` and `workflows.adapter` internally, not public graph internals.

## Plugin facade staging

- Implemented public facade remains `api.llm`, `api.tools`, `api.stores`, and `api.events`.
- `api.plugins` remains implemented.
- `api.workflow` remains implemented.
- `api.engine` is implemented and remains provisional.
- `api.runtime` remains deferred.
- `api.errors` is implemented.

## Config-facing concepts

Configuration taxonomy is defined in `../../configuration/model/CONFIGURATION.md`.
Schema boundaries, validation layering, and source precedence are defined in `../../configuration/schema/CONFIG_SCHEMA.md`.
API surface remains separate from config-facing concepts.

These concepts are controlled by config rather than arbitrary imports:

- workflow enabled / disabled
- graph_kind / workflow_kind
- LLM profile
- tool allowlist
- limits
- observability capture level
- store backend
- worker backend
- UI visibility

Forbidden config behavior:

- arbitrary Python import
- `safety.enabled = false`
- raw prompt or full response persistence
- secret values in config payloads
- allow all tools by default
- provider raw response persistence

## P0-A done when

- public / provisional / internal / config-facing / future are classified.
- public vocabulary is workflow-oriented while internal vocabulary may remain graph-oriented.
- Tool / LLM / Store / EventSink / Error candidates are summarized.
- internal-only modules are listed.
- `workflows/catalog.py` is treated as internal / semi-internal composition.
- arbitrary import from config is rejected.
- safety cannot be disabled by config.
- `cobalt_wren.api.engine` is implemented as the package facade, while `cobalt_wren.api.runtime` remains deferred.


## Config Surface

- No public `api.config` facade exists yet.
- `cobalt_wren.config.*` is internal/provisional.
- Config Core Block B is intentionally not part of the public facade.


## Config Validation Surface

- `cobalt_wren.config.*` remains internal/provisional.
- `ConfigValidator` is internal/provisional and is not exposed through `api.config`.
- `EffectivePluginSet` and `ValidatedPackageConfig` are internal config models.
- public facade work is still limited to `api.llm`, `api.tools`, `api.stores`, `api.events`, `api.errors`, and `api.plugins`.


## Runtime Surface

- No public `api.runtime` facade exists yet.
- `cobalt_wren.runtime.*` is internal/provisional.
- runtime assembly is not part of the public facade yet.

## Application Workflow Policy

Application workflow authors should use the public facades:

- `cobalt_wren.api.errors`
- `cobalt_wren.api.plugins`
- `cobalt_wren.api.workflow`
- `cobalt_wren.api.engine`
- `cobalt_wren.api.llm`
- `cobalt_wren.api.tools`
- `cobalt_wren.api.stores`
- `cobalt_wren.api.events`

Internal / provisional APIs:

- `cobalt_wren.config.*`
- `cobalt_wren.runtime.*`
- `cobalt_wren.plugins.registry`
- `cobalt_wren.workflows.adapter`
- `cobalt_wren.workflows.requirements`
- `cobalt_wren.workflows.prepare`
- `cobalt_wren.workflows.catalog`

Internal foundation:

- legacy `cobalt_wren.graphs.*` package: removed; no compatibility import is provided

Control plane:

- `cobalt_wren.apps.automation.*`

Application workflows are expected to use the public facades first and to keep control-plane dependencies out of workflow packages.

## Package Facade Surface

`cobalt_wren.api.engine` is the implemented public-facing provisional package facade.
Block M verifies the `create_engine` -> `prepare_workflow` path through this facade.

It hides internal package mechanics:

- `PluginRegistry`
- `WorkflowPreparer`
- `workflows.catalog`
- `workflows.prepare`
- `workflows.adapter`
- `workflows.requirements`
- `ConfigValidator`
- `RuntimeAssembler`
- `RuntimeDependencies`

`run_workflow` and `api.runtime` remain deferred because they would prematurely expose graph execution, checkpoint/resume, worker/queue, and long-running runtime contracts.

The service-layer workflow preparation bridge is transitional and should eventually route through `api.engine` rather than package internals directly.

## Package-Facing Boundary

`cobalt_wren.api.engine` is the package-facing facade for application/control-plane code.
It hides `PluginRegistry`, `WorkflowPreparer`, `RuntimeAssembler`, `ConfigValidator`, `RuntimeDependencies`, `workflows.catalog`, `workflows.prepare`, `workflows.adapter`, and `workflows.requirements`.
`run_workflow` and `api.runtime` remain deferred.
`apps/automation/services/workflow_preparation.py` now routes through `api.engine`; the transitional exception has been removed.

## Workflow Runtime Contract

The public workflow surface now includes `WorkflowBuildContext`, `WorkflowExecutable`, and `WorkflowExecutionResult`. `AutomationEngine.prepare_workflow(..., config=...)` passes opaque workflow-specific config through the public build context. `EnginePreparedWorkflow.execute(...)` normalizes capability-based execution without requiring LangGraph types.

The supported executable capabilities are, in order, `execute`, `invoke`, and callable. This is an adapter boundary rather than a promise that arbitrary return types are accepted: execution must return a mapping or `WorkflowExecutionResult`.

## Optional Installed Plugin Discovery

Installed distributions may publish a zero-argument plugin factory or a `Plugin` instance through the Python entry-point group `cobalt_wren.plugins`. Discovery is opt-in:

```python
engine = create_engine(config, discover_plugins=True)
```

Explicit `plugins=(...)` registration remains the primary deterministic path. An explicit plugin wins when a discovered entry point returns a plugin with the same plugin name. Contribution conflicts between differently named plugins continue to fail through `PluginRegistrationError`.

`discover_plugins()` imports entry-point targets but does not execute contribution validation or provider/tool/store factories. Load failures and invalid results are normalized as safe `PluginResolutionError` values.

## Prepared Workflow Handle

`EnginePreparedWorkflow.executable` is the sole opaque implementation handle. Normal consumers should call `execute(...)`; framework-specific consumers may inspect `executable` without receiving guarantees beyond object identity.

Workflow preparation order is now:

1. resolve contribution
2. validate a defensive copy of workflow-specific config
3. validate runtime requirements
4. construct `WorkflowBuildContext`
5. call `build(context)`

Validation failures use the safe code `WORKFLOW_CONFIG_INVALID` and do not execute requirements-dependent work or the workflow builder.

## Control-plane Execution Integration

The Django Run service resolves public workflows from `Workflow.definition_payload`, prepares them through the deployment engine owner, and executes them through the same persisted lifecycle used by the internal LangGraph path.

## Django Workflow Reference

The control plane selects an installed/public workflow when `Workflow.definition_payload` contains `{"workflow": {"kind": "...", "config": {...}}}`. Missing `workflow` preserves the legacy graph path; malformed references fail closed and do not fall back to a graph.

`RunExecutionServices` owns a lazy, process-scoped deployment engine. The engine is assembled once on first public preparation and reused across runs. Both public and legacy execution adapters normalize into the framework-neutral `ControlPlaneExecutionResult` before Run persistence.

Top-level public-path observability follows `EnginePreparedWorkflow.lifecycle_events_owner`. The default is `control_plane`; `workflow` suppresses control-plane lifecycle emission to avoid duplicate run events.

## Deployment Engine Reload

`RunExecutionServices.reconfigure_engine(...)` and `DeploymentEngineOwner.reconfigure(...)` provide an explicit single-process reload boundary. A candidate engine is fully constructed before atomic swap; failures retain the last-known-good generation. `force=True` rebuilds even when the deployment signature is unchanged.

Prepared handles expose `engine_generation` and a hashed `engine_signature`. These values describe the engine snapshot used at preparation and do not change after a later reload. Reload is process-local and does not provide Python module hot replacement or cross-worker synchronization.

## Current Execution Surface

`EnginePreparedWorkflow.executable` is the sole opaque executable handle. `execute(..., context=WorkflowExecutionContext(...))` is the execution boundary. The Django control plane resolves only `WorkflowReference` values and has no graph-specific runtime or fallback contract. LangGraph may be used inside workflow implementations.

`RunExecutionServices` and `DeploymentEngineOwner` are internal control-plane composition helpers. `api.runtime` remains deferred. True resume requires an explicit package checkpoint / LangGraph `BaseCheckpointSaver` convergence design.

## Workflow Integration API Surface

`cobalt_wren.api.integrations` is the provisional public SPI for official and external workflow-OSS helpers. It contains framework-neutral definitions, capability and availability descriptors, projection DTOs, action DTOs, and `WorkflowIntegrationProvider`.

The internal `WorkflowIntegrationRegistry` stores centrally declared definitions, checks target distribution/import availability, validates supported version ranges, lazy-loads provider implementations, and resolves only explicitly named integrations. Automatic target inference remains deferred.

The generic workflow adapter does not import this registry or branch on integration identity. Integration providers wrap targets before those targets reach the existing capability adapter.

Provisional projection and action vocabulary:

- `ExecutionUnitProjection`
- `LifecycleProjection`
- `IntegrationProjection`
- `IntegrationProjectionBatch`
- `IntegrationActionDescriptor`
- `IntegrationActionRequest`

These DTOs define a semantic boundary only. They do not grant persistence, rendering, or execution authority by themselves. Framework-specific payloads remain versioned and attached to canonical owners instead of being flattened into the canonical schema.
