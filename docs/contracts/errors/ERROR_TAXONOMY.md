---
type: contract
status: current
authority: normative
summary: Stable public error categories, safe payload shape, and execution-stage normalization.
code_refs:
  - src/cobalt_wren/api/errors.py
  - src/cobalt_wren/workflows/prepare.py
  - src/cobalt_wren/apps/automation/services/execution.py
  - src/cobalt_wren/apps/automation/services/runs.py
test_refs:
  - tests/unit/api/test_error_contracts.py
  - tests/unit/api/test_public_errors_imports.py
  - tests/unit/automation/test_run_execution_public_workflow.py
verified:
  date: 2026-07-23
  commit: WORKTREE
  base_commit: ed0702a
  method:
    - code-and-test-review
---
# Error Taxonomy

This document defines the error taxonomy for `cobalt-wren`.

Purpose:

- separate framework-wide error categories
- separate safe user-facing messages from internal diagnostics
- preserve the primary failure when secondary failures occur
- ensure EventSink / observability failures never overwrite the primary failure
- wrap arbitrary exceptions from plugin hooks into framework error categories
- fix error boundaries before `ConfigLoader`, `PluginRegistry`, `ConfigValidator`, and `RuntimeAssembly` exist
- keep `api.errors` as a future facade for the broader taxonomy
- the staged public facade for minimal `api.errors` is defined in `../../api/errors/API_ERRORS_FACADE.md`

## Design principles

- User-facing safe messages and internal diagnostics are distinct.
- Error categories should match component boundaries.
- Configuration, plugin, runtime, execution, and safety failures should not be mixed.
- Secondary failures must not replace the primary failure.
- Raw exception messages must not be copied directly into UI, API, or `Run.error_message`.
- Diagnostics must also be bounded and redacted.
- Error taxonomy should not be frozen into the public API too early.
- `api.errors` minimal facade is implemented, but the broader taxonomy remains staged.
- `ErrorCode` enum / `ErrorCategory` enum are not implemented in this phase.

Coupling rules:

- `ConfigValidator` may create validation errors, but not runtime assembly errors.
- `PluginRegistry` may create registration and resolution errors, but not runtime dependency construction errors.
- `RuntimeAssembly` may create dependency construction errors, but not raw schema errors.
- `WorkflowExecutable` execution may create execution errors, but not plugin registration errors.

## Error categories

- `ConfigurationError`
- `PluginRegistrationError`
- `PluginResolutionError`
- `PluginValidationError`
- `RuntimeAssemblyError`
- `ExecutionError`
- `ToolPolicyError`
- `ToolExecutionError`
- `ToolOutputSafetyError`
- `ProviderExecutionError`
- `StoreError`
- `CheckpointStoreError`
- `EventSinkError`
- `SafetyBoundaryError`
- `InternalInvariantError`

These are taxonomy categories, not a commitment to one class per category.
MVP may use a smaller surface such as `FrameworkError` plus category/code fields.

## ConfigurationError

`ConfigurationError` covers raw config, normalized config, and schema validation failures.

Typical cases:

- invalid schema version
- unknown top-level field
- unknown core field
- unsafe config field
- secret literal
- arbitrary import path
- invalid provider profile reference
- invalid workflow kind reference
- invalid tool allowlist reference
- invalid limits
- invalid observability config
- invalid store backend config

Boundary:

- configuration source / schema / semantic validation failures belong here
- runtime assembly factory failures do not

Safe message example:

- `Configuration is invalid: unknown provider profile 'default'.`

Do not expose:

- raw config bodies
- secret-like values
- env var values
- absolute file paths
- full tracebacks
- provider raw objects

## PluginRegistrationError

`PluginRegistrationError` covers failures during manual registration.

Typical cases:

- duplicate plugin name
- duplicate contribution name in the same scope
- invalid plugin metadata
- invalid contribution metadata
- unsupported plugin type
- incompatible plugin API version
- override denied

Boundary:

- registration-time failures belong here
- lookup failures belong to `PluginResolutionError`

Safe message example:

- `Plugin registration failed: duplicate tool contribution 'github.search_issues'.`

Bounded diagnostics may include:

- plugin name
- contribution type
- contribution name
- conflicting provider plugin name

Do not expose:

- plugin object repr
- raw object memory address
- secret-bearing metadata
- full traceback in user-facing output

## PluginResolutionError

`PluginResolutionError` covers failures to resolve configured names through the registry.

Typical cases:

- enabled but not registered plugin
- disabled plugin contribution referenced
- unknown workflow kind
- unknown tool name
- unknown provider name
- unknown store backend
- unknown event sink backend
- unknown worker backend

Safe message example:

- `Plugin resolution failed: workflow kind 'company_agent' is not registered.`

Boundary:

- lookup failures belong here
- plugin-specific validation failures belong to `PluginValidationError`
- concrete factory failures belong to `RuntimeAssemblyError`

## PluginValidationError

`PluginValidationError` covers failures from plugin-specific validation hooks.

Typical cases:

- `workflows.<name>.config` is invalid
- provider-specific profile parameters are invalid
- tool-specific config is invalid
- store backend config is invalid
- event sink backend config is invalid
- UI metadata config is invalid

Policy:

- arbitrary exceptions raised by plugin hooks must be wrapped
- raw exception messages must not be exposed directly

Safe message example:

- `Workflow configuration for 'company_agent' is invalid: missing required field 'departments'.`

Diagnostics may include:

- plugin name
- contribution name
- validation hook name
- bounded/redacted exception summary

## RuntimeAssemblyError

`RuntimeAssemblyError` covers concrete dependency construction failures.

Typical cases:

- provider factory failure
- tool factory failure
- artifact store factory failure
- checkpoint store factory failure
- event sink factory failure
- worker adapter factory failure
- missing secret env var
- invalid secret resolver result
- factory returned invalid type

Boundary:

- validation failures do not belong here
- runtime assembly failures do not belong to raw config schema categories

Safe message example:

- `Runtime assembly failed: provider 'litellm' could not be initialized.`

Do not expose:

- env var values
- API keys
- auth headers
- credential-bearing URLs
- provider raw objects
- full tracebacks

## ExecutionError

`ExecutionError` covers workflow execution failures.

Typical cases:

- graph execution failure
- invalid state transition
- unexpected node failure
- output mapping failure
- checkpoint read/write during execution
- artifact persistence during execution

Run lifecycle:

- `Run.error_message` stores a safe summary only
- `Run.output_payload` stores a safe summary only

Safe message example:

- `Workflow execution failed.`

Workflow or node identifiers may be included only if they are bounded and non-sensitive.

## ToolPolicyError / ToolExecutionError / ToolOutputSafetyError

Tool failures are split to keep policy, execution, and safety distinct.

`ToolPolicyError`:

- tool execution denied by workflow policy
- tool capability denied
- disabled plugin tool referenced

Safe message example:

- `Tool execution denied by policy.`

`ToolExecutionError`:

- allowed tool execution failed
- timeout
- external API failure
- tool input runtime failure
- tool output validation failure

Safe message example:

- `Tool execution failed.`

`ToolOutputSafetyError`:

- raw `ToolResult.output` attempted to persist
- secret-like value detected in tool output summary
- output too large for safe metadata

Safe message example:

- `Tool output was rejected by a safety boundary.`

## ProviderExecutionError

`ProviderExecutionError` covers LLM / embedding provider call failures.

Typical cases:

- provider timeout
- provider rate limit
- provider authentication failure
- provider response invalid
- provider raw response rejected
- `LLMResult` construction failure

Safe message example:

- `LLM provider request failed.`

Diagnostics may include:

- provider name
- model name
- error category
- retryable / non-retryable signal

Do not expose:

- full prompt
- full response
- API key
- auth header
- raw provider object

## StoreError

`StoreError` covers artifact and checkpoint store failures.

Typical cases:

- artifact write failure
- artifact read failure
- checkpoint write failure
- checkpoint read failure
- checkpoint schema version mismatch
- storage backend unavailable
- retention / size limit exceeded

Safe message examples:

- `Artifact store operation failed.`
- `Checkpoint store operation failed.`

Diagnostics may include:

- store backend
- operation
- logical id
- schema version

Do not expose:

- absolute local path
- raw checkpoint body
- raw artifact content
- secret-bearing storage URL

## CheckpointStoreError

`CheckpointStoreError` covers versioned checkpoint repository failures.

Typical cases:

- invalid checkpoint identity
- immutable identity conflict
- stale parent conflict
- checkpoint body corruption
- unsupported serializer version
- storage backend unavailable

Safe message examples:

- `Checkpoint request is invalid.`
- `Checkpoint identity conflicts with an existing immutable version.`
- `Checkpoint persistence failed.`

Boundary:

- versioned checkpoint storage failures belong here
- latest-state replacement is no longer part of the checkpoint contract
- raw checkpoint body, identity, or metadata must not be exposed

## EventSinkError

`EventSinkError` covers observability sink failures.

Primary rule:

- `EventSinkError` must not override the primary failure

Example:

- primary: `ProviderExecutionError`
- secondary: `EventSinkError` while recording that provider failure

The primary failure safe message must remain the externally visible one.

Allowed event metadata:

- `error.category`
- `error.code`
- `error.component`
- `error.safe_message`
- `retryable`

Careful:

- diagnostic message only if redacted and bounded

Forbidden:

- raw exception object
- full traceback
- secret
- raw prompt
- raw tool output

## SafetyBoundaryError

`SafetyBoundaryError` covers safety and redaction contract violations.

Typical cases:

- secret-like literal detected in config
- raw `Run.input_payload` attempted to persist into graph state
- raw LLM response attempted to persist
- raw tool output attempted to persist
- full traceback attempted to expose
- absolute local path attempted to expose
- provider raw object attempted to persist

This category is closer to framework contract violation than ordinary runtime failure.

Safe message example:

- `A safety boundary prevented unsafe data exposure.`

The unsafe value itself must not be included in the message or diagnostics.

## InternalInvariantError

`InternalInvariantError` covers impossible framework states.

Typical cases:

- validated config missing a required normalized field
- registry returns an unexpected contribution type
- factory returns an invalid object
- impossible run state transition
- graph runtime receives invalid execution input

Safe message example:

- `Internal framework invariant failed.`

This should be user-facing as a generic failure, with bounded diagnostics only.

## FrameworkError candidate fields

Future framework error objects may carry:

- `category`
- `code`
- `safe_message`
- `diagnostic_message`
- `retryable`
- `component`
- `cause`
- `metadata`

Field guidance:

- `category`: configuration / plugin registration / plugin resolution / plugin validation / runtime assembly / execution / tool policy / tool execution / provider execution / store / event sink / safety / internal invariant
- `code`: stable machine-readable code
- `safe_message`: message allowed in UI / API / `Run.error_message`
- `diagnostic_message`: internal only
- `component`: config_loader / plugin_registry / config_validator / runtime_assembly / graph_runtime / tool / provider / store / event_sink
- `cause`: original exception, not for direct UI/API exposure
- `metadata`: redacted and bounded only

## Error code policy

Potential codes:

- `CONFIG_UNKNOWN_FIELD`
- `CONFIG_SECRET_LITERAL`
- `CONFIG_ARBITRARY_IMPORT`
- `CONFIG_INVALID_SCHEMA_VERSION`
- `CONFIG_UNKNOWN_PROVIDER_PROFILE`
- `PLUGIN_DUPLICATE_NAME`
- `PLUGIN_CONTRIBUTION_CONFLICT`
- `PLUGIN_UNKNOWN`
- `PLUGIN_DISABLED`
- `PLUGIN_INCOMPATIBLE_API_VERSION`
- `PLUGIN_VALIDATION_FAILED`
- `RUNTIME_ASSEMBLY_PROVIDER_FAILED`
- `RUNTIME_ASSEMBLY_TOOL_FAILED`
- `RUNTIME_ASSEMBLY_STORE_FAILED`
- `RUNTIME_ASSEMBLY_SECRET_MISSING`
- `RUNTIME_ASSEMBLY_INVALID_FACTORY_RESULT`
- `TOOL_POLICY_DENIED`
- `TOOL_EXECUTION_FAILED`
- `TOOL_OUTPUT_UNSAFE`
- `PROVIDER_REQUEST_FAILED`
- `PROVIDER_RESPONSE_INVALID`
- `STORE_ARTIFACT_FAILED`
- `STORE_CHECKPOINT_FAILED`
- `STORE_CHECKPOINT_VERSION_MISMATCH`
- `EVENT_SINK_FAILED`
- `SAFETY_RAW_INPUT_PERSISTENCE`
- `SAFETY_RAW_LLM_RESPONSE_PERSISTENCE`
- `SAFETY_RAW_TOOL_OUTPUT_PERSISTENCE`
- `SAFETY_SECRET_EXPOSURE`
- `SAFETY_TRACEBACK_EXPOSURE`
- `INTERNAL_INVARIANT_FAILED`

This document does not define an enum or code implementation.

## safe_message and diagnostic_message

`safe_message`:

- intended for user / UI / API / `Run.error_message`

`diagnostic_message`:

- intended for internal logs / debug / developer use
- still bounded and redacted

Example:

- safe: `Plugin registration failed: duplicate tool contribution 'github.search_issues'.`
- diagnostic: `Plugin 'github_tools_v2' tried to register tool 'github.search_issues', already provided by plugin 'github_tools'.`

## Run lifecycle

- `Run.error_message` stores `safe_message` only
- `Run.output_payload` stores safe summary only
- internal diagnostics may be preserved in logs, spans, or event metadata when redacted and bounded
- raw config, raw prompt, raw response, raw tool output, secrets, env var values, and absolute paths do not belong in `Run.error_message`

## Primary failure preservation

- primary failure = the original processing failure
- secondary failure = cleanup, observability, event sink, or recording failure

Rule:

- secondary failure must not replace the primary failure

Example:

- primary: `ProviderExecutionError`
- secondary: `EventSinkError` while recording that provider error

The primary failure category, code, and safe message remain the externally visible result.

## Retryable and non-retryable

Potential retryable cases:

- provider timeout
- provider rate limit
- temporary store unavailable
- temporary event sink unavailable

Potential non-retryable cases:

- invalid config
- unknown plugin
- duplicate plugin
- unsafe config
- missing required workflow config
- tool policy denied
- incompatible plugin API version

This document does not define the retry system itself.

## Plugin hook exception wrapping

Arbitrary exceptions from plugin-provided hooks must be wrapped by the framework.

Examples:

- plugin validation hook exception -> `PluginValidationError`
- plugin factory hook exception -> `RuntimeAssemblyError`
- tool callable exception -> `ToolExecutionError`
- provider client exception -> `ProviderExecutionError`

Raw exception messages are not automatically safe.
The framework owns safe message construction.

## api.errors

The minimal public facade is implemented in `src/cobalt_wren/api/errors.py` and staged in `../../api/errors/API_ERRORS_FACADE.md`.
The broader taxonomy remains staged here for future extensions.

Implemented public facade:

- `FrameworkError`
- `ConfigError`
- `PluginRegistrationError`
- `PluginResolutionError`
- `PluginValidationError`
- `RuntimeAssemblyError`
- `SafetyBoundaryError`

Deferred or internal candidates:

- `ExecutionError`
- `ToolPolicyError`
- `ToolExecutionError`
- `ToolOutputSafetyError`
- `ProviderExecutionError`
- `StoreError`
- `EventSinkError`
- `InternalInvariantError`

`ErrorCode` enum / `ErrorCategory` enum are not implemented in this phase.


## Workflow-stage categories

- `workflow_preparation`: workflow-specific configuration or executable construction failed after package dependencies were assembled.
- `execution`: an unexpected executable failure was normalized at the control-plane boundary.

Unexpected exceptions are converted to `ExecutionError` with `WORKFLOW_EXECUTION_FAILED`. The persisted and observable message is redacted and bounded before it crosses the control-plane result boundary. Existing `FrameworkError` instances retain their original category and code.
