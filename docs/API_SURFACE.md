# API Surface

This document defines the boundary between public, provisional, internal, config-facing, and future APIs for `langgraph-automation`.

The goal is to keep the package small on the outside, flexible on the inside, and safe for future plugin authors who should not depend on internal implementation details.

## API stability levels

- `Public`: stable surface that external plugin authors and application workflows may import.
- `Provisional`: likely future public surface, but still subject to change.
- `Internal`: package implementation detail; do not import from outside the package.
- `Config-facing`: concepts that are controlled through config, not by arbitrary Python imports.
- `Future`: directionally planned, but not implemented yet.

## Public API principles

- Keep the public API narrow.
- Expose public APIs through facades, not by encouraging deep imports.
- Plugin authors should not import internal modules directly.
- Public vocabulary should prefer `workflow` where user-facing terms are needed.
- Internal implementation may continue to use `graph` vocabulary.
- Config may adjust behavior, but it must not allow arbitrary imports or safety bypasses.

## Future public module layout

The following layout is a candidate for later phases.

- `langgraph_automation.api`
- `langgraph_automation.api.workflow`
- `langgraph_automation.api.runtime`
- `langgraph_automation.api.tools`
- `langgraph_automation.api.llm`
- `langgraph_automation.api.stores`
- `langgraph_automation.api.events`
- `langgraph_automation.api.errors`

Package P0-A is docs only. Minimal facade or re-export modules may be considered in Package P0-B.

## Workflow API surface

Current internal foundation names remain graph-oriented:

- `GraphDefinition`
- `GraphRuntimeRequirements`
- `UnknownGraphKindError`

Future public vocabulary may be workflow-oriented:

- `WorkflowDefinition`
- `WorkflowRequirements`
- `UnknownWorkflowKindError`

Decisions:

- Do not rename `GraphDefinition` now.
- A future public facade may introduce `WorkflowDefinition` as an alias or wrapper.
- `workflows/catalog.py` is package composition, not a public API surface.
- Plugin authors should move toward a future registration API rather than editing catalog internals directly.

## Runtime API surface

Current candidates:

- `GraphRuntime`
- `GraphExecutionInput`
- `GraphRuntimeConfig`

Guidance:

- `GraphRuntime` is a provisional candidate, not a frozen public contract.
- A future `WorkflowRuntime` protocol or facade may replace direct reliance on the concrete class.
- `GraphExecutionInput` is the transient raw input boundary and may later be renamed toward `WorkflowExecutionInput`.
- `GraphRuntimeConfig` is graph-local runtime configuration and must never carry secrets or raw input.
- Do not over-freeze the concrete `GraphRuntime` class before the package surface is designed.

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

Internal-only handling:

- concrete `LiteLLMClient`
- provider-specific raw payload handling
- settings / env secret resolution

Guidance:

- Workflow nodes should not import concrete providers.
- `LLMResult.raw` must not be stored in state, output, or events.
- Provider raw objects must not cross the safe boundary.

## Store API surface

Current candidates:

- `ArtifactStore`
- `CheckpointStore`

Future concepts:

- `ArtifactStorePlugin`
- `CheckpointStorePlugin`
- `LocalFileArtifactStore`
- `S3ArtifactStore`
- persistent checkpoint backend

Guidance:

- Persistent stores are future work.
- Storage keys and file paths must remain redaction-safe.
- Absolute local file paths must not appear in UI or API output.

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

Error taxonomy is not being implemented in this phase.

Future public candidates may include:

- `WorkflowConfigurationError`
- `UnknownWorkflowKindError`
- `RuntimeDependencyError`
- `ToolPolicyDeniedError`
- `ProviderError`
- `ExecutionError`

Current guidance:

- Do not rename internal graph error classes now.
- `UnknownGraphKindError` remains the internal graph vocabulary for this phase.
- A future public facade may map graph vocabulary to workflow vocabulary.

## Internal-only modules

The following should be treated as internal-only for plugin authors and external consumers:

- `langgraph_automation.apps.automation.services.*`
- `langgraph_automation.apps.automation.models`
- `langgraph_automation.graphs.runner`
- `langgraph_automation.graphs.builders`
- `langgraph_automation.workflows.catalog`
- `langgraph_automation.core.result_safety`
- `langgraph_automation.core.redaction`
- concrete integration modules
- Django settings and model internals

Notes:

- `graphs/registry.py` is the current foundation registry mechanism, but external consumers should not depend on it as a permanent public contract.
- `workflows/catalog.py` is package composition internal / semi-internal.
- A future registration API should become the supported path for extending workflows.

## Config-facing concepts

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
- `GraphDefinition` / `GraphRuntimeRequirements` have a future public facade strategy.
- `GraphRuntime` / `GraphExecutionInput` / `GraphRuntimeConfig` have a documented public strategy.
- Tool / LLM / Store / EventSink / Error candidates are summarized.
- internal-only modules are listed.
- `workflows/catalog.py` is treated as internal / semi-internal composition.
- arbitrary import from config is rejected.
- safety cannot be disabled by config.
- `langgraph_automation.api.*` is still not implemented.
