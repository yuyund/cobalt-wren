# 0012. api.errors minimal facade

Status: Accepted

## Context

The framework-wide error taxonomy is now documented across configuration, plugin registration, plugin resolution, plugin validation, runtime assembly, execution, provider/tool/store/event sink, safety, and internal invariant boundaries.

Before implementing `ConfigLoader`, `PluginRegistry`, `ConfigValidator`, `RuntimeAssembly`, or `api.plugins`, the minimal public error surface needs to be staged.

Publishing too many concrete error subclasses too early would couple the public API to provider, tool, store, and event sink implementation details. Publishing `ErrorCode` or `ErrorCategory` enums too early would freeze granularity before implementation validates it.

## Decision

- `api.errors` remains unimplemented in this phase
- the initial public facade candidates are `FrameworkError`, `ConfigError`, `PluginRegistrationError`, `PluginResolutionError`, `PluginValidationError`, `RuntimeAssemblyError`, and `SafetyBoundaryError`
- `ExecutionError`, `ToolPolicyError`, `ToolExecutionError`, `ToolOutputSafetyError`, `ProviderExecutionError`, `StoreError`, `EventSinkError`, and `InternalInvariantError` remain deferred or internal candidates
- fine-grained reasons are represented by `category` and `code` rather than many public subclasses
- MVP uses `category: str` and `code: str`; `ErrorCode` and `ErrorCategory` enums are deferred
- `diagnostic_message` is not part of the initial stable public field set, or remains internal-only if added later
- `metadata` must be redacted and bounded
- `cause` is kept for exception chaining and is not user-facing
- unsafe config values are represented as `ConfigError`, while runtime data-flow / persistence / exposure violations are represented as `SafetyBoundaryError`
- `RuntimeAssemblyError` is reserved for concrete dependency construction after validation and registry lookup

## Consequences

- the public error API remains small and stable
- `ConfigLoader`, `PluginRegistry`, `ConfigValidator`, and `RuntimeAssembly` can use shared framework errors without depending on each other's internals
- provider / tool / store / event sink implementation details are not prematurely exposed
- `safe_message` remains the only user-facing message
- later implementation can refine code and category granularity without changing many public subclasses
