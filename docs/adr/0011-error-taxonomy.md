# 0011. Error taxonomy

Status: Accepted

## Context

Package P3-D staged the plugin API facade. Before implementing `api.plugins`, `ConfigLoader`, `PluginRegistry`, `ConfigValidator`, or `RuntimeAssembly`, the framework needs a fixed error boundary.

Without a taxonomy, safe user-facing messages, internal diagnostics, plugin validation failures, runtime assembly failures, and observability failures would be easy to mix. Secondary failures could also overwrite the primary failure, which would weaken `Run` lifecycle reliability.

## Decision

- error categories are separated by component boundary: configuration, plugin registration, plugin resolution, plugin validation, runtime assembly, execution, tool policy, tool execution, provider execution, store, event sink, safety boundary, and internal invariant
- framework errors separate `safe_message` from `diagnostic_message`
- `Run.error_message` stores `safe_message` only
- `diagnostic_message` is internal and must be redacted and bounded
- secondary failure must not replace the primary failure
- `EventSinkError` must not override the primary failure
- plugin validation hook exceptions are wrapped as `PluginValidationError`
- plugin factory hook exceptions are wrapped as `RuntimeAssemblyError`
- provider / tool / store / event sink execution failures are categorized separately
- `SafetyBoundaryError` never includes unsafe values themselves
- `api.errors` remains a future facade; no error classes are implemented in this phase

## Consequences

- `ConfigValidator`, `PluginRegistry`, `RuntimeAssembly`, `GraphRuntime`, and `EventSink` can evolve with separate error boundaries
- UI/API safe messages remain decoupled from internal diagnostics
- plugin author exceptions can be wrapped without leaking raw messages
- later `api.errors` implementation can stay minimal and intentional
- primary failure preservation remains a framework-wide invariant
