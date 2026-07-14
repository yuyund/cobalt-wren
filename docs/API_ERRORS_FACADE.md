# api.errors Minimal Facade

This document defines the minimal public facade policy for `langgraph_automation.api.errors`.

Implementation status:

- minimal facade is implemented
- public error classes are exported from `src/langgraph_automation/api/errors.py`

Purpose:

- map the framework-wide error taxonomy into a minimal public facade
- define the smallest set of public error class candidates
- define deferred and internal error candidates
- avoid subclass explosion
- preserve the boundary between safe messages and diagnostics
- keep the facade separate from `ConfigLoader`, `PluginRegistry`, `ConfigValidator`, and `RuntimeAssembly`

## Design principles

- Keep the public error surface minimal.
- Public errors should represent framework boundaries.
- Internal errors should represent implementation details and concrete provider / tool / store / event sink failures.
- Prefer `category` and `code` over many public subclasses.
- `safe_message` is for user-facing output, UI, API, and `Run.error_message`.
- `diagnostic` is internal-only, redacted, and bounded.
- Raw exception messages must not be automatically adopted as `safe_message`.
- Provider, tool, store, and event sink execution errors are taxonomy members, but they are not part of the initial public facade.
- `api.errors` is a shared surface for later implementations, but it must not hold registry, validator, or runtime assembly internals.

Coupling rules:

- `ConfigLoader` and `ConfigValidator` use `ConfigError`-style errors.
- `PluginRegistry` uses `PluginRegistrationError` and `PluginResolutionError`.
- `ConfigValidator` uses `PluginValidationError`.
- `RuntimeAssembly` uses `RuntimeAssemblyError`.
- safety boundary violations use `SafetyBoundaryError`.
- provider, tool, store, and event sink execution errors remain taxonomy members, but are deferred from the initial public facade.

## Implemented public facade

Implemented public facade:

- `FrameworkError`
- `ConfigError`
- `PluginRegistrationError`
- `PluginResolutionError`
- `PluginValidationError`
- `RuntimeAssemblyError`
- `SafetyBoundaryError`

`__all__` exports the same set.

## Public minimal candidates

Initial public facade candidates:

- `FrameworkError`
- `ConfigError`
- `PluginRegistrationError`
- `PluginResolutionError`
- `PluginValidationError`
- `RuntimeAssemblyError`
- `SafetyBoundaryError`

### FrameworkError

`FrameworkError` is the base candidate for public framework failures.

### ConfigError

`ConfigError` covers config source, schema, and semantic validation failures.

### PluginRegistrationError

`PluginRegistrationError` covers manual plugin registration failures.

### PluginResolutionError

`PluginResolutionError` covers registry lookup failures and enabled-plugin mismatches.

### PluginValidationError

`PluginValidationError` covers plugin-specific validation hook failures and safe wrapping.

### RuntimeAssemblyError

`RuntimeAssemblyError` covers concrete dependency construction failures after validation and registry lookup.

### SafetyBoundaryError

`SafetyBoundaryError` covers unsafe raw input, raw provider object, raw tool output, traceback exposure, and unsafe persistence violations.

## Deferred and internal candidates

Deferred or internal candidates:

- `ExecutionError`
- `ToolPolicyError`
- `ToolExecutionError`
- `ToolOutputSafetyError`
- `ProviderExecutionError`
- `StoreError`
- `EventSinkError`
- `InternalInvariantError`

Reasons:

- `ExecutionError` depends on `GraphRuntime` and workflow execution boundaries that are still evolving.
- `ToolPolicyError` depends on `ToolPolicy` semantics.
- `ToolExecutionError` depends on the tool callable / adapter boundary.
- `ToolOutputSafetyError` depends on tool result persistence safety.
- `ProviderExecutionError` depends on provider abstraction, retry, and provider implementation details.
- `StoreError` depends on artifact and checkpoint store implementation details.
- `EventSinkError` depends on observability capture policy and primary failure preservation.
- `InternalInvariantError` is framework-internal and does not need a public subclass in the initial facade.

These errors may still exist in the taxonomy and may be represented by `category` / `code`, but they are deferred from the initial public facade.

## Minimal class hierarchy

Recommended minimal hierarchy:

```text
FrameworkError
  ├─ ConfigError
  ├─ PluginRegistrationError
  ├─ PluginResolutionError
  ├─ PluginValidationError
  ├─ RuntimeAssemblyError
  └─ SafetyBoundaryError
```

MVP guidance:

- do not create a subclass per individual reason
- use `code` for specific conditions instead

Avoid:

- `ConfigUnknownFieldError`
- `ConfigSecretLiteralError`
- `PluginDuplicateNameError`
- `PluginContributionConflictError`
- `ProviderTimeoutError`
- `ProviderRateLimitError`
- `ToolTimeoutError`
- `StoreCheckpointVersionMismatchError`
- `EventSinkTimeoutError`

Reason:

- a long public subclass list freezes implementation detail too early
- category / code keeps the API smaller and easier to evolve

## FrameworkError candidate fields

Candidate fields:

- `safe_message`
- `code`
- `category`
- `component`
- `retryable`
- `metadata`
- `cause`

Field guidance:

- `safe_message`: safe user-facing summary
- `code`: machine-readable reason string
- `category`: broad component boundary
- `component`: narrower source like `config_loader`, `plugin_registry`, `config_validator`, `runtime_assembly`, `graph_runtime`, `tool`, `provider`, `store`, or `event_sink`
- `retryable`: whether retry may make sense
- `metadata`: redacted and bounded only
- `cause`: original exception for chaining, not for direct UI/API exposure

`diagnostic_message` is not part of the initial stable public field set. If it appears later, it should remain internal-only and redacted/bounded.

`metadata` sanitizer is not implemented yet; the contract remains redacted / bounded only.

## Category / code as subclass alternatives

Fine-grained distinctions should use category and code, not extra subclasses.

Examples:

- class: `PluginRegistrationError`
- category: `plugin_registration`
- code: `PLUGIN_DUPLICATE_NAME`
- safe_message: `Plugin registration failed: duplicate plugin name 'github'.`

Another example:

- class: `ConfigError`
- category: `config`
- code: `CONFIG_SECRET_LITERAL`
- safe_message: `Configuration is invalid: secret-like literal is not allowed.`

## ErrorCode and ErrorCategory policy

MVP:

- `code: str`
- `category: str`

Future:

- `ErrorCode` enum or literal aliases may be considered later
- `ErrorCategory` enum may be considered later

Initial category candidates:

- `config`
- `plugin_registration`
- `plugin_resolution`
- `plugin_validation`
- `runtime_assembly`
- `safety`

The broader taxonomy also includes provider, tool, store, event sink, execution, and internal invariant concepts. Those do not need to be public enum values in the initial facade.

## diagnostic_message

Recommended policy:

- do not make `diagnostic_message` part of the initial public stable field set
- if it exists later, keep it internal-only
- always redact and bound it

Reason:

- plugin authors may accidentally include unsafe detail
- it can be confused with `safe_message`
- it is safer to connect it later to logging and event sinks

## metadata

`metadata` is useful, but it must stay bounded.

Policy:

- redacted and bounded only
- JSON-like primitives only
- no raw objects

Allowed examples:

- `plugin_name: "github"`
- `contribution_name: "github.search_issues"`
- `provider_name: "litellm"`
- `component: "plugin_registry"`
- `field: "plugins.enabled"`

Forbidden examples:

- raw config dict
- API key
- auth header
- full prompt
- raw provider response
- raw tool output
- Django model object
- exception object
- absolute local path
- credential-bearing URL

Suggested shape:

- `Mapping[str, JSONScalar | Sequence[JSONScalar]]`

This is conceptual only. Implementation should preserve sanitizer and redaction boundaries.

## cause

`cause` is for exception chaining and internal diagnosis.

Policy:

- never expose `cause` directly in UI/API
- do not use `cause` as `safe_message`
- prefer standard chaining such as `raise ... from exc`

Raw cause messages are not automatically safe.

## Errors plugin author may raise

Plugin authors may raise:

- `PluginValidationError`
- `RuntimeAssemblyError`
- `SafetyBoundaryError`

Framework wrapping rules:

- plugin validation hook arbitrary exception -> `PluginValidationError`
- plugin factory hook arbitrary exception -> `RuntimeAssemblyError`

Even when plugin authors use those errors directly, the framework should still normalize messages and redact unsafe detail.

## ConfigError and SafetyBoundaryError boundary

Use `ConfigError` for unsafe config values discovered during config validation.

Examples:

- secret literal in config -> `ConfigError(code=CONFIG_SECRET_LITERAL)`
- arbitrary import path in config -> `ConfigError(code=CONFIG_ARBITRARY_IMPORT)`

Use `SafetyBoundaryError` for runtime data-flow, persistence, or exposure violations.

Examples:

- raw `Run.input_payload` attempted to persist -> `SafetyBoundaryError(code=SAFETY_RAW_INPUT_PERSISTENCE)`
- raw `ToolResult.output` attempted to persist -> `SafetyBoundaryError(code=SAFETY_RAW_TOOL_OUTPUT_PERSISTENCE)`

This keeps config validation separate from runtime safety enforcement.

## RuntimeAssemblyError boundary

`RuntimeAssemblyError` is reserved for concrete dependency construction after validation and registry lookup.

Use it for:

- `ProviderContribution.create_client` failure
- `ToolContribution.create_tool` failure
- `StoreContribution.create_store` failure
- `EventSinkContribution.create_sink` failure
- `SecretResolver` failure
- factory returned invalid object

Do not use it for:

- unknown provider name -> `PluginResolutionError`
- invalid provider config -> `ConfigError` or `PluginValidationError`
- duplicate plugin -> `PluginRegistrationError`

## Provider / tool / store / event sink errors

`ProviderExecutionError`, `ToolExecutionError`, `StoreError`, and `EventSinkError` exist in the taxonomy, but they remain deferred from the initial public facade.

Reason:

- they are tightly coupled to concrete integration details
- they tend to drag retry / timeout / external API semantics into the public surface too early
- the initial facade should stay small and stable

## safe_message construction

The framework owns `safe_message` construction.

Plugin-provided detail may be used as input, but the final message must be normalized by the framework.

Example:

- plugin raises: `ValueError("API key sk-xxx is invalid")`
- framework wraps: `PluginValidationError(safe_message="Plugin validation failed for 'github'.", code="PLUGIN_VALIDATION_FAILED", category="plugin_validation", ...)`

Raw exception messages are not automatically safe.

## Run.error_message

`Run.error_message` should store `FrameworkError.safe_message` when available.

For arbitrary exceptions, a helper such as `safe_run_error_message()` remains the last-line defense for producing a safe summary.

This facade does not replace existing safety helpers.

## EventSink and diagnostic handling

Event sink metadata may include:

- `error.category`
- `error.code`
- `error.component`
- `error.safe_message`
- `error.retryable`

Diagnostics, cause chains, and secondary failures must remain redacted and bounded.

EventSink or logging failures must not replace the primary failure.

## Implementation phases

Phase E1:

- docs/API_ERRORS_FACADE.md
- docs/adr/0012-api-errors-facade.md

Phase E2:

- `src/langgraph_automation/api/errors.py`
- minimal import tests

Phase E3:

- `ConfigLoader`, `PluginRegistry`, `ConfigValidator`, and `RuntimeAssembly` use the public error facade

This phase is documentation only.

## P3-E / P1-C / later connections

- P3-E Minimal api.plugins facade implementation may surface `PluginValidationError`, `RuntimeAssemblyError`, and `SafetyBoundaryError` to plugin authors
- P1-C Config loader / normalizer MVP needs `ConfigError`
- P3-F Manual PluginRegistry MVP needs `PluginRegistrationError` and `PluginResolutionError`
- P1-D ConfigValidator MVP needs `ConfigError`, `PluginResolutionError`, `PluginValidationError`, and `SafetyBoundaryError`
- RuntimeAssembly MVP needs `RuntimeAssemblyError`

`api.errors` is worth designing before those implementations so the eventual public surface stays small and intentional.
