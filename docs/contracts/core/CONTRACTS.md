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

## GraphExecutionInput Contract

- raw `Run.input_payload` の transient boundary
- `GraphRuntime.execution_input` として渡す
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
- FilesystemCheckpointStore is implemented in `langgraph_automation.integrations.checkpoint`.

## Configuration Schema Contract

- `RawPackageConfig` is source-facing and is not consumed by runtime assembly directly.
- `ValidatedPackageConfig` is package-level normalized config and contains no secret values or concrete runtime objects.
- `ResolvedWorkflowConfig` is workflow-specific resolved config and does not include `Run.input_payload`.
- `Run.input_payload` is execution input, not config override.
- `RuntimeAssembly` resolves names to concrete dependencies.
- `GraphRuntimeConfig` contains only graph-local safe config.
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
- `GraphDefinition` and `GraphRuntime` remain internal foundation vocabulary
- `PluginRegistry` stores workflow contributions only
- `PluginRegistry` does not build or execute workflows
- built-in/reference workflows use the same `Plugin` / `WorkflowContribution` path as external workflows
- `workflows.adapter` is the only place that calls `WorkflowDefinition.build`
- `workflows.requirements` is the internal `WorkflowRequirements` / `RuntimeDependencies` checker
- `ConfigValidator` does not validate workflow configs yet
- `RuntimeAssembler` does not execute workflows
- `api.runtime` is not part of `api.workflow`

## Plugin API Facade Contract

- implemented public facade remains `api.llm`, `api.tools`, `api.stores`, `api.events`, `api.errors`, `api.plugins`, and `api.workflow`
- `api.runtime` remains deferred
- `GraphRuntime` and `GraphDefinition` remain outside the public facade
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

## GraphRuntimeConfig Contract

- execution-plane config は graph-local
- secret や raw input を入れない
- API key / base URL / provider raw object を入れない
- workflow config を runtime 用の安全な最小面へ変換する

`GraphRuntime` is currently a public candidate but still provisional. `GraphDefinition` is also internal foundation vocabulary for now; a future public facade may expose `WorkflowDefinition` as an alias or wrapper.

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
- `FilesystemCheckpointStore` is implemented in `langgraph_automation.integrations.checkpoint` and is `PROCESS_DURABLE`
- checkpoint runtime selection is controlled by typed config and the canonical builder
- `MemoryCheckpointStore` remains the default checkpoint backend when the section is absent
- `FilesystemCheckpointStore` is explicit opt-in and is constructed from typed config exactly once per runtime assembly
- true resume is still deferred
- DB metadata には checkpoint body copy を入れない

## P0-B Public Facade Contract

- `langgraph_automation.api.llm`
- `langgraph_automation.api.tools`
- `langgraph_automation.api.stores`
- `langgraph_automation.api.events`

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
- `apps/automation/services/workflow_config.py` should remain graph-free after the P0 audit fix.
- This direct execution adapter boundary is temporary and should eventually route through a dedicated execution facade such as `api.runtime`.
- The execution facade remains deferred; this contract only acknowledges the current adapter responsibility.

## Package Facade Contract

- package complete requires an application-facing package facade
- the implemented provisional facade module name is `langgraph_automation.api.engine`
- the facade must hide `PluginRegistry`, `WorkflowPreparer`, `workflows.catalog`, `workflows.prepare`, `workflows.adapter`, `workflows.requirements`, `ConfigValidator`, `RuntimeAssembler`, and `RuntimeDependencies`
- `create_engine` accepts raw package config plus explicit plugins
- explicit plugins passed to `create_engine` are registered and auto-enabled for validation and runtime assembly
- `AutomationEngine.prepare_workflow` returns a public-facing provisional `EnginePreparedWorkflow`
- `EnginePreparedWorkflow.graph` is opaque and must not become a stable public contract
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
- `langgraph_automation.api.engine` is the allowed package-facing boundary
- `apps/automation/services/workflow_preparation.py` now routes through `api.engine`; the temporary exception has been removed
- `apps/automation` must not grow new direct imports into `graphs.*`, `runtime.*`, `workflows.prepare`, `workflows.catalog`, `workflows.adapter`, `workflows.requirements`, `plugins.registry`, or `config.validator` outside the explicit execution adapters above
- exact allowlists for the execution adapters are enforced by architecture guards
- `workflows/applications` should treat `graphs.*` as provisional and not public API, only using it where required for `WorkflowDefinition.build`
