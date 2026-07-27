---
type: contract
status: current
authority: normative
summary: Current framework-neutral workflow, service, safety, and lifecycle contracts.
code_refs:
  - src/cobalt_wren/api/workflow.py
  - src/cobalt_wren/workflows/adapter.py
  - src/cobalt_wren/apps/automation/services
test_refs:
  - tests/unit/architecture/test_public_run_single_path.py
  - tests/unit/architecture/test_execution_lifecycle_convergence_boundary.py
verified:
  date: 2026-07-23
  commit: WORKTREE
  base_commit: 8e2f19b9ed39bb3b5bf2ce07bbc31cbd58587e33
  method:
    - code-and-test-review
---
# Contracts

This document fixes the boundaries between execution foundation, workflows, and services.

These contracts describe the current internal foundation surface. If parts of this surface become public later, they should do so through a facade, alias, or protocol rather than by exposing internal modules directly.

## Node Contract

- node は state patch dict を返す
- node は Django ORM を直接触らない
- node は concrete provider を import しない
- node は concrete tool を import しない
- node は raw input_payload を state に入れない
- node は raw LLM response / raw ToolResult.output を state に入れない

## Runner Contract

- runner は `ExecutionResult` を返す
- `ExecutionResult.output_payload` は service 層へ渡す output candidate
- runner は Run model を直接更新しない
- runner は safe persistence の責務を持たない

## Service Contract

- service 層が Run lifecycle を管理する
- service 層が `safe_run_output_payload()` で `Run.output_payload` を正規化する
- service 層が `safe_run_error_message()` で `Run.error_message` を正規化する

## Run.output_payload Contract

- `Run.output_payload` は UI/API に出せる safe summary
- raw prompt / raw response / raw tool output / secrets を含めない
- provider raw object を含めない
- traceback を含めない
- `safe_run_output_payload()` の結果だけを保存する

## Safety Exposure Contract

- admin / dynamic UI は summary fields を表示する
- `Run.input_payload` は controlled raw input store だが、UI/admin/event/span/output/checkpoint に raw copy しない
- `Run.error_message` は `safe_run_error_message()` の結果だけを保存する
- traceback-like multiline input は切り詰めて最後の診断行だけを残す
- `EventSink` と `DjangoEventSink` は metadata only / bounded / redacted を守る
- artifact body と checkpoint body は store 側に残し、DB には metadata だけを保存する


- raw `Run.input_payload` の transient boundary
- checkpointable state には入れない
- state には `input_summary` のみ入れる
- UI/admin/event に raw input を流用しない

## Configuration Contract

- Package-level config, `Workflow.definition_payload`, and `Run.input_payload` are different layers.
- Package-level config holds deployment / provider / plugin / policy / store / observability defaults.
- `Workflow.definition_payload` is database-backed workflow instance-specific config.
- `Run.input_payload` is a single execution input, not runtime config.
- Normalized runtime config is package config plus validated `Workflow.definition_payload`.
- physical persistence configuration is application-composition scoped and bound once into run services
- `start_run()` / `retry_run()` consume bound run services, not raw package config or per-run backend/root values
- `Run.input_payload` must not be used to read model, `api_key`, `base_url`, or `tools.allowed`.
- artifact backend selection is represented by `stores.artifact`
- missing `stores.artifact` normalizes to `MemoryArtifactStore`
- explicit filesystem selection requires an absolute root and startup-only construction
- runtime selection must not silently fall back from filesystem to memory
- checkpoint backend selection is represented by `stores.checkpoint`
- missing `stores.checkpoint` normalizes to `MemoryCheckpointStore`
- explicit filesystem checkpoint selection requires an absolute root and startup-only construction
- checkpoint runtime selection must not silently fall back from filesystem to memory
- FilesystemCheckpointStore is implemented in `cobalt_wren.integrations.checkpoint`.

## Configuration Schema Contract

- `RawPackageConfig` is source-facing and is not consumed by runtime assembly directly.
- `ValidatedPackageConfig` is package-level normalized config and contains no secret values or concrete runtime objects.
- `ResolvedWorkflowConfig` is workflow-specific resolved config and does not include `Run.input_payload`.
- `Run.input_payload` is execution input, not config override.
- `RuntimeAssembly` resolves names to concrete dependencies.
- artifact store config is typed and selected once during runtime assembly

## api.plugins Contract

- plugin objects are metadata + contributions only
- contributions hold definitions / hooks, not concrete runtime instances
- registry stores plugin definitions, not runtime dependencies
- registry raises `PluginRegistrationError` for registration conflicts
- registry raises `PluginResolutionError` for unknown lookups
- registry does not call validation hooks or factory hooks

## Plugin API Contract

- plugin code must not depend on internal modules
- plugin-specific config validation is owned by the plugin type
- core schema keeps plugin-specific config opaque
- tool plugins remain subject to ToolPolicy
- provider / store / event plugins are resolved by name through registry boundaries

## Plugin Registration Contract

- duplicate registration is rejected in Package MVP
- override is denied by default
- config does not import plugins
- `plugins.enabled` references registered plugin names
- registry provides lookup and duplicate detection only
- validator orchestrates validation and runtime assembly constructs dependencies later

## Plugin API Shape Contract

- plugin objects contain metadata and contributions
- workflow contributions are declared through `api.workflow`
- contribution validation hooks do not create runtime dependencies
- contribution factory hooks are called by RuntimeAssembly
- registry does not hold concrete runtime instances
- ValidationContext and FactoryContext must not contain raw config source, Run object, Django ORM object, or secret values unless mediated by SecretResolver

## Workflow API Contract

- `api.workflow` is the public workflow vocabulary facade
- `WorkflowContribution` is declarative and does not execute workflows
- `WorkflowDefinition.build` is retained on the definition shape, but `PluginRegistry` does not call it
- `PluginRegistry` stores workflow contributions only
- `PluginRegistry` does not build or execute workflows
- bundled examples or future built-in workflows, if added, must use the same `Plugin` / `WorkflowContribution` path as external workflows; the current built-in catalog is empty
- `workflows.adapter` is the only place that calls `WorkflowDefinition.build`
- `workflows.requirements` is the internal `WorkflowRequirements` / `RuntimeDependencies` checker
- `ConfigValidator` does not validate workflow configs yet
- `RuntimeAssembler` does not execute workflows
- `api.runtime` is not part of `api.workflow`

## Plugin API Facade Contract

- implemented public facade remains `api.llm`, `api.tools`, `api.stores`, `api.events`, `api.errors`, `api.plugins`, and `api.workflow`
- `api.runtime` remains deferred
- PluginRegistry, ConfigValidator, and RuntimeAssembly are not public facade types in P3-D

## Error Taxonomy Contract

- `Run.error_message` stores safe message only
- `diagnostic_message` is internal and must be redacted and bounded
- secondary failure must not replace primary failure
- plugin hook exceptions are wrapped into framework error categories
- `EventSinkError` does not override primary failure
- `SafetyBoundaryError` never includes unsafe values themselves
- traceback-like multiline text is collapsed before persistence

## api.errors Facade Contract

- `str(error)` is `safe_message`
- `to_safe_dict()` excludes `cause`, traceback, and `diagnostic_message`
- `metadata` must be redacted and bounded
- subclass category is fixed
- `code` and `category` remain strings in MVP
- `ErrorCode` and `ErrorCategory` enums are not implemented
- the public error surface starts minimal
- fine-grained reasons are represented by category / code rather than subclass explosion
- `safe_message` is the only user-facing message
- `diagnostic` is internal-only, redacted, and bounded
- `metadata` must not contain raw config, secret, prompt, provider response, tool output, Django model object, or absolute local path
- `cause` is not user-facing


- execution-plane config は graph-local
- secret や raw input を入れない
- API key / base URL / provider raw object を入れない
- workflow config を runtime 用の安全な最小面へ変換する


## Tool Contract

- tool result は安全な summary を返す
- raw tool output は state / output / EventSink に戻さない
- policy deny は observable だが、raw secret を含めない

## LLM Contract

- LLM result は raw object をそのまま state に流さない
- provider raw object は永続化しない
- model / token count / bounded summary は許可される
- secrets を messages に混ぜても永続化しない

## EventSink Contract

- EventSink は observability boundary
- EventSink payload は redaction-safe である
- EventSink failure は primary failure を上書きしない
- payload / metadata に raw prompt, raw response, raw tool output, absolute path, secret-like value を入れない

## ArtifactStore Contract

- artifact store は metadata と body を分離する
- body is bytes
- request / descriptor / read result are separated
- current memory store is EPHEMERAL and guarantees immutable write / idempotent write / conflict detection
- current filesystem store is PROCESS_DURABLE and guarantees content-addressed immutable body publication, deterministic manifest writes, idempotent retry, and conflict detection
- `FilesystemArtifactStore` verifies manifest and body integrity on read
- size and digest are store-derived
- metadata は normalized / redacted / defensive copy で扱う
- raw secrets / raw provider payload を保存しない
- DB metadata には body copy を入れない
- `MemoryArtifactStore` remains the default artifact backend
- `FilesystemArtifactStore` is explicit opt-in and is constructed from typed config exactly once per runtime assembly

## CheckpointStore Contract

- checkpoint store contract is versioned and append-only
- checkpoint storage is a versioned execution-state repository
- `CheckpointWriteRequest`, `StoredCheckpoint`, and `CheckpointReadResult` separate request / descriptor / read-result responsibilities
- execution stream identity is `run_id + checkpoint_namespace`
- complete checkpoint identity is `run_id + checkpoint_namespace + checkpoint_id`
- `checkpoint_id` is caller-issued and immutable
- `revision` is store-assigned and orders versions within a stream
- `parent_checkpoint_id` is the expected current head and records lineage
- `save(request)` is append-only, idempotent for the same canonical request, and conflict-aware for stale parents or changed content
- `load_latest()`, `load_checkpoint()`, and `list_for_run()` are the supported read operations
- `list_for_run()` returns descriptors only and is ordered by revision
- `delete(run_id)` is not part of the versioned checkpoint contract
- serializer identity, serializer version, content type, size, digest, and safe JSON-compatible metadata are part of the durable descriptor
- accepted checkpoint metadata is preserved as a lossless logical JSON value and is not redacted during persistence
- returned checkpoint metadata is defensively isolated from stored state
- `MemoryCheckpointStore` is the EPHEMERAL semantic reference implementation
- `CheckpointStore` audit result is `APPROVED_FOR_IMPLEMENTATION`
- `FilesystemCheckpointStore` is implemented in `cobalt_wren.integrations.checkpoint` and is `PROCESS_DURABLE`
- checkpoint runtime selection is controlled by typed config and the canonical builder
- `MemoryCheckpointStore` remains the default checkpoint backend when the section is absent
- `FilesystemCheckpointStore` is explicit opt-in and is constructed from typed config exactly once per runtime assembly
- true resume is still deferred
- DB metadata には checkpoint body copy を入れない

## P0-B Public Facade Contract

- `cobalt_wren.api.llm`
- `cobalt_wren.api.tools`
- `cobalt_wren.api.stores`
- `cobalt_wren.api.events`

These modules re-export selected foundation interfaces. They do not expose workflow definition, runtime concrete implementation, plugin loader, config loader, or public error taxonomy yet. `LLMRequest` is a provisional loose alias for request shape, not a provider-specific contract.

## OutputCandidate / NodeResult

現時点の判断:

- OutputCandidate dataclass: まだ導入しない
- NodeResult dataclass: まだ導入しない

現時点では:

- node return = state patch dict
- `ExecutionResult.output_payload` = output candidate dict


## Config Core Contract

- loader accepts Mapping input only in MVP
- loader returns `RawPackageConfig`
- normalizer returns `NormalizedPackageConfig`
- Config Core does not import `PluginRegistry`
- Config Core does not call plugin validation hooks
- Config Core does not call factory hooks
- Config Core does not resolve secret values
- unsafe config is `ConfigError`
- safety cannot be disabled


## Config Validation Contract

- `ConfigValidator` is the first layer allowed to import `PluginRegistry`
- `ConfigValidator` derives an `EffectivePluginSet` from `plugins.enabled`
- registered plugins do not imply enabled plugins
- contribution references are resolved against `EffectivePluginSet`, not raw registry state
- `ConfigValidator` may call plugin-specific validation hooks
- `ConfigValidator` must not call factory hooks
- validation-hook arbitrary exceptions are wrapped as `PluginValidationError`
- tool configs outside allowlist are `ConfigError`


## Runtime Assembly Contract

- `RuntimeAssembler` accepts `ValidatedPackageConfig`
- `RuntimeAssembler` uses `EffectivePluginSet`
- `RuntimeAssembler` does not perform config validation
- `RuntimeAssembler` does not call validation hooks
- `RuntimeAssembler` calls factory hooks with keyword arguments only
- arbitrary factory exceptions are wrapped as `RuntimeAssemblyError`
- secrets are resolved through `SecretResolver` / `FactoryContext`
- secret values are not merged into config
- secret values are not stored in `RuntimeDependencies` metadata
- `RuntimeAssemblyError` is used for missing factories, unsupported store types, and invalid factory results

## Application Workflow Contract

- application workflow must be modeled as `Plugin` + `WorkflowContribution`
- application workflow must declare `WorkflowRequirements`
- application workflow must not construct `RuntimeDependencies` directly
- application workflow must not call `RuntimeAssembler` directly
- application workflow must not perform `PluginRegistry` registration by itself
- application workflow must not import Django models or settings
- application workflow must not import `apps.automation` services
- application workflow must not persist raw provider or tool output
- application workflow must not store secret values in metadata

## Workflow Preparation Contract

- `WorkflowPreparer` accepts `PluginRegistry` and `RuntimeDependencies`
- `WorkflowPreparer` resolves `WorkflowContribution` by workflow kind
- `WorkflowPreparer` checks requirements before build
- `WorkflowPreparer` calls `WorkflowDefinition.build` only through `workflows.adapter`
- `WorkflowPreparer` does not call `WorkflowContribution.validate_config`
- `WorkflowPreparer` does not execute graphs
- `WorkflowPreparer` does not call `RuntimeAssembler`
- `WorkflowPreparer` does not call `ConfigValidator`
- `PreparedWorkflow` is an internal preparation result, not a public runtime API

## Service Integration Contract

- service layer may call `WorkflowPreparer`
- service layer may create the built-in workflow registry
- application workflow code must not call `WorkflowPreparer` directly
- service layer must preserve safe output and safe error contracts
- service layer must not persist raw input, prompt, or provider response
- service layer must not call `ConfigValidator` or `RuntimeAssembler` through `WorkflowPreparer`

## Control-Plane Execution Adapter Contract

- `apps/automation/services/runtime.py`, `execution.py`, and `runs.py` are the current control-plane execution adapters.
- These adapters may import `graphs.runtime`, `graphs.runner`, `graphs.registry`, `graphs.config`, and `workflows.catalog` for the current direct execution path.
- The allowed direct imports should be exact and should not spread to new `apps/automation` modules.
- deleted graph/config adapters must not be reintroduced into the control-plane execution path.
- This direct execution adapter boundary is temporary and should eventually route through a dedicated execution facade such as `api.runtime`.
- The execution facade remains deferred; this contract only acknowledges the current adapter responsibility.

## Package Facade Contract

- package complete requires an application-facing package facade
- the implemented provisional facade module name is `cobalt_wren.api.engine`
- the facade must hide `PluginRegistry`, `WorkflowPreparer`, `workflows.catalog`, `workflows.prepare`, `workflows.adapter`, `workflows.requirements`, `ConfigValidator`, `RuntimeAssembler`, and `RuntimeDependencies`
- `create_engine` accepts raw package config plus explicit plugins
- explicit plugins passed to `create_engine` are registered and auto-enabled for validation and runtime assembly
- `AutomationEngine.prepare_workflow` returns a public-facing provisional `EnginePreparedWorkflow`
- `EnginePreparedWorkflow.executable` is opaque; `execute(...)` is the normal execution surface
- application/control-plane code should use the facade rather than package internals
- the current service bridge is transitional and must not be treated as the final architecture
- the facade should provide a small supported entrypoint for package context creation and workflow preparation
- the facade should not prematurely expose `run_workflow`, full workflow execution, graph runner internals, or checkpoint/resume semantics
- `api.runtime` remains deferred until the runtime contract is designed explicitly
- facade-level verification should cover the `create_engine` -> `prepare_workflow` path without requiring provider network calls or graph execution
- safe failures must surface `FrameworkError`-derived safe messages only
- raw traceback, secret values, and provider raw payloads must not leak through `safe_message`

## Boundary Hardening Contract

- application/control-plane code must not couple directly to package internals
- `cobalt_wren.api.engine` is the allowed package-facing boundary
- `apps/automation/services/workflow_preparation.py` now routes through `api.engine`; the temporary exception has been removed
- `apps/automation` must not grow new direct imports into `graphs.*`, `runtime.*`, `workflows.prepare`, `workflows.catalog`, `workflows.adapter`, `workflows.requirements`, `plugins.registry`, or `config.validator` outside the explicit execution adapters above
- exact allowlists for the execution adapters are enforced by architecture guards
- `workflows/applications` should treat `graphs.*` as provisional and not public API, only using it where required for `WorkflowDefinition.build`

## Internal Loose Coupling Contract

- Loose coupling applies to package internals and public consumers.
- Public API, plugin-author SPI, internal orchestration, concrete adapters, control-plane composition, UI projection, and rendering are separate stability domains.
- Config loading, structural parsing, normalization, semantic validation, plugin resolution, secret resolution, and runtime construction must remain separable.
- External library models and raw objects must not become package-wide contracts unless intentionally mapped into package-owned vocabulary.
- No-op forwarding and speculative abstractions without replacement or extension evidence are not required contracts.

## Workflow Flexibility Contract

- workflow state, topology, routing, subgraphs, LLM use, tool use, artifact use, checkpoint use, and workflow-specific config are workflow-owned choices.
- adding a workflow must not require changes to existing workflow code, graph foundation, runtime assembly, or control-plane services unless a new package capability is required.
- foundation contracts constrain safety and integration, not business topology.

## Dynamic UI Projection Contract

- renderer input is an explicit safe UI specification, not an unrestricted Django model.
- field, relation, and action allowlists are mandatory.
- raw payloads, private service maps, and renderer-side Django `_meta` introspection are forbidden.
- reusable UI semantics, Django query/model adapters, control-plane registration, and renderer implementation must remain separable.

## Persistence Convergence Contract

- artifact identity, checkpoint version semantics, physical storage, execution persistence orchestration, LangGraph saver behavior, and control-plane metadata are distinct responsibilities.
- PROCESS_DURABLE filesystem storage does not imply true execution resume.
- package `CheckpointStore`, LangGraph `BaseCheckpointSaver`, pending writes, thread identity, checkpoint namespace, serializer, retry, time travel, and `CheckpointMetadata` require an explicit convergence design before resume implementation.

## Internal Loose Coupling Contract

The control plane, runtime assembler, workflow preparer, executable, persistence stores, observability decorators, and UI projection are separate responsibility boundaries. Workflow implementations may use any internal library without making that library part of the package contract.

## Workflow Flexibility Contract

A workflow is selected by `workflow.kind`, receives opaque workflow config, declares requirements, and builds an executable from `WorkflowBuildContext`. Adding a workflow must not require a graph registry, control-plane branch, or foundation-specific runtime bundle.

## Dynamic UI Projection Contract

Dynamic UI renders safe metadata projections only. It does not execute workflows, construct runtime capabilities, resolve secrets, or expose raw payloads.

## Workflow OSS Integration Contract

- `api.integrations` contains framework-neutral SPI vocabulary only.
- `IntegrationDefinition` centrally declares identity, target distribution/import, provider path, supported version range, maturity, priority, capabilities, limitations, documentation, and auto-detection eligibility.
- integration target distributions remain optional deployment dependencies.
- provider implementation loading is lazy.
- explicit integration selection is implemented; automatic inference is deferred.
- `WorkflowIntegrationRegistry` is internal and does not import Django, control-plane modules, the generic workflow adapter, or concrete workflow frameworks.
- availability inspection checks import and distribution metadata without loading provider implementation.
- provider definitions must exactly match centrally registered definitions.
- duplicate, unknown, missing, incompatible, invalid, and load-failed integrations fail through safe plugin registration/resolution errors.

## Integration Projection And Action Contract

- canonical execution units and lifecycle events use package-owned DTOs.
- framework-specific detail uses versioned `IntegrationProjection` payloads attached to canonical owner identities.
- actions are declared as data through `IntegrationActionDescriptor` and requested through `IntegrationActionRequest`.
- projection/action DTOs defensively copy top-level mappings.
- framework objects, pickles, compiled graphs, handles, and private object dumps are not valid projection payloads.
- future control-plane persistence, renderer composition, and action routing must remain separate from these DTO definitions.

## Integration Action Routing Contract

- `integration.actions.v1` is a framework-neutral persisted descriptor schema.
- an action descriptor is a UI and audit snapshot, not execution authority.
- the server revalidates Run policy, active projection ownership and expiry, descriptor availability, action support, and current executable capability on every submission.
- the common router currently executes only `resume`; unsupported action IDs fail closed.
- integration resume uses the existing `dispatch_resume` path and therefore supports both inline execution and `ExecutionJobOperation.RESUME`.
- UI permission maps integration actions to `automation.resume_run`.
- action request audit payloads are stored through the existing safe summary boundary.
- the common action router does not import or branch on a workflow framework.

## LlamaIndex Workflows Integration Contract

- the optional target distribution is `llama-index-workflows>=2.22,<3`; it is not a mandatory package dependency.
- integration identity is `llamaindex-workflows`.
- the provider uses public run, handler, streamed-event, and step-state APIs only.
- step lifecycle maps to canonical `step` spans and `llamaindex.step.v1`.
- streamed events map to bounded `llamaindex.event.v1` projections.
- step success is not finalized until the stream has ruled out a following `WorkflowFailedEvent`.
- synchronous EventSink operations are buffered while the async handler runs and replayed in synchronous execution context.
- resume, waiting, checkpoints, external event actions, and cancellation routing are unsupported and declared as such.

## Integration Projection Semantics Contract

- `projection_kind` is one of `snapshot`, `event`, `reference`, or `action`.
- `owner_kind` identifies the canonical persisted record relationship; `subject_kind` and `subject_external_id` identify what the projection describes.
- snapshot subjects must be stable across lifecycle transitions; framework task-attempt IDs may remain in payload or owner metadata but are not the current-state identity.
- `occurred_at`, `sequence`, and record identity define deterministic timeline order.
- current state selects the latest snapshot per integration, subject kind, subject identity, and schema.
- event, reference, and action records do not overwrite current snapshot state.
- all records remain append-only and available through technical projection detail until expiry.

## External OSS Integration Distribution Contract

- external workflow packages publish contributions through the `cobalt_wren.plugins` entry-point group.
- external OSS workflow packages may depend on public integration helpers but must not import control-plane, registry, preparation, runtime-assembly, persistence, or renderer internals.
- a separately installed plugin must be discoverable without explicit `Plugin` object injection.
- clean-room verification builds and installs both foundation and plugin wheels, migrates an isolated database, resolves database-backed workflow references, executes contributed workflows, persists spans and projections, and renders Run detail UI.
- framework dependencies are declared by the external distribution when the distribution provides workflows for those frameworks.
- wheel installation and entry-point discovery are required evidence before claiming distribution-level neutrality.

## Optional Workflow OSS Dependency Contract

- the foundation project dependencies do not include LangGraph or LlamaIndex Workflows.
- `langgraph`, `llamaindex`, and `oss-integrations` are explicit optional extras.
- importing the engine facade, empty built-in workflow catalog, public integration helpers, and Native examples must not import a target workflow OSS.
- concrete integration provider modules may import their target OSS because they are loaded lazily after availability and version resolution.
- plain Python executable compatibility is a separate lower-level SPI and is verified independently from Native examples.
- external plugin distributions declare the framework dependencies required by their contributed workflows.

## Integration Availability And Health UI Contract

- integration health presentation is built from central definitions, registry availability, and safe provider resolution results.
- missing or incompatible targets do not load provider modules.
- provider loading is attempted only when target import and distribution version are compatible.
- provider load failures, invalid providers, and definition mismatches render fixed diagnostics without causes, tracebacks, private paths, or exception messages.
- installation guidance comes from definition metadata and never from runtime exception text.
- capability and limitation rendering is framework-neutral and does not branch on integration ID.
- the combined UI health status distinguishes a ready integration from an installed target whose provider cannot load.

## Native Authoring Direction Contract

- Native Authoring is a convenience and execution layer that produces ordinary public workflow contributions.
- the primary authoring model preserves normal Python control flow and requires explicit named step boundaries for orchestration behavior.
- step callables remain ordinary synchronous or asynchronous Python functions and must be directly unit-testable.
- the `workflow` decorator must not parse Python AST, infer a complete static DAG, rewrite control flow, or serialize local variables.
- Native uses the generic workflow adapter, canonical Run lifecycle, EventSink, integration projection persistence, common actions, and common UI; it receives no private control-plane path.
- Native MVP supports bounded business pipelines, branching, bounded iteration, step observation, cooperative cancellation, providers, tools, and artifacts.
- retry and timeout attach to explicit step execution boundaries and do not imply idempotency or hard termination of arbitrary synchronous code.
- Native MVP does not promise checkpoint continuation, durable waiting, deterministic replay, time travel, state fork, exactly-once side effects, arbitrary distributed fan-out, or stateful subgraphs.
- LangGraph remains the recommended integration when durable stateful graph semantics are required.
- Native projections are versioned and framework-neutral UI composition must not branch on the Native integration ID.

## Native Authoring P1 Contract

- `cobalt_wren.native` is the provisional public Native facade.
- `workflow(...)` attaches metadata and returns a `NativeWorkflow`; it does not alter the wrapped function's Python control flow.
- `NativeWorkflow.contribution(...)` and `.plugin(...)` produce ordinary public contract objects.
- Native execution is async-first and explicit named steps accept synchronous and asynchronous callables.
- synchronous step callables execute through a worker thread and must not access thread-affine resources without an application-owned adapter.
- each started Native step has a stable logical subject name, ordered sequence, canonical `step` span, and `native.step.v1` snapshot.
- synchronous EventSink operations are buffered during async execution and replayed after coroutine completion or failure.
- Native step failure re-raises the original exception but retained step diagnostics use a fixed safe error message.
- execution control is checked before a step and after its callable returns; cancellation between steps prevents the next step from starting.
- direct synchronous Native execution from an active event loop is unsupported and fails explicitly.
- reusable step definitions, artifact helpers, progress, metrics, and durable waiting are not implemented by P2A.

## Bundled Workflow Integration Boundary Contract

- a bundled workflow or authoring implementation does not receive a private foundation execution path.
- Native authoring objects are converted by the official `native` integration provider before the generic workflow adapter sees them.
- the generic preparer, adapter, engine facade, Django execution service, Run lifecycle, persistence services, and UI must not import Native implementation modules or branch on the `native` integration ID.
- bundled and external workflows use the same `WorkflowContribution`, opaque executable, execution context, EventSink, projection persistence, action routing, and UI composition contracts.
- Native, LangGraph, and LlamaIndex capabilities and health are declared through the same central integration definition and registry vocabulary.
- bundling affects package availability and registration only; it does not change runtime semantics or control-plane privileges.

## Native Authoring P2 Policy Contract

- retry and timeout remain Native integration execution semantics and do not add branches to the generic foundation path.
- `RetryPolicy` is explicit and retry does not imply callable idempotency.
- every attempt receives a separate canonical step Span while all attempts for one call share a stable occurrence subject.
- intermediate attempt failure produces a `retrying` snapshot; only the last exhausted attempt produces `failed`.
- retained retry diagnostics use fixed safe messages and never persist the original exception text.
- cancellation and workflow deadline checks occur before attempts, during retry delays, and after callables return.
- the effective step timeout is the smaller of the requested step timeout and remaining workflow deadline.
- asynchronous callables are cancelled by the timeout boundary; synchronous callables may continue in their worker thread after the awaiting workflow times out.
- a terminal step timeout raises `WorkflowTimeoutError` and is normalized by the common control plane to a timed-out Run.
- repeated step calls require a safe occurrence key; occurrence identities are unique within one Run.
- occurrence keys are bounded safe identifiers and the Native executor enforces a maximum of 1,000 step occurrences per Run.

## Native Examples Contract

- the foundation currently ships no product workflows and the built-in workflow catalog is empty.
- Native examples live under `examples/native/` and are not imported or registered by the engine.
- examples demonstrate public authoring behavior but do not establish stable workflow kinds, compatibility promises, or control-plane privileges.
- applications explicitly register example-derived or application-owned plugins, or publish them through the normal plugin entry-point group.
- generic preparation, execution, persistence, and UI paths remain verified by explicit test plugins rather than implicit examples.
- plain Python executable compatibility remains a separate lower-level SPI contract.
