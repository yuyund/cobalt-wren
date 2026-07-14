# LangGraph Automation

This repository contains a Django-based control plane around LangGraph execution. The app is organized to keep workflow selection, runtime assembly, and node execution loosely coupled.

Detailed design documents live under `docs/`:

- `docs/CODEX_WORKFLOW.md`
- `docs/ROADMAP.md`
- `docs/ARCHITECTURE.md`
- `docs/CONTRACTS.md`
- `docs/API_SURFACE.md`
- `docs/CONFIGURATION.md`
- `docs/CONFIG_SCHEMA.md`
- `docs/adr/`

## Architecture Overview

- `apps/automation/services` owns lifecycle and configuration validation.
- `graphs` owns execution foundation code: graph selection mechanics, registry mechanics, runner, runtime helpers, and graph-local state contracts.
- `integrations` owns concrete adapters for LLMs, tools, artifact stores, checkpoint stores, and observability.
- `workflows` owns concrete workflow composition and reference/application workflow boundaries.
- `core` owns safety and summary helpers used across layers.
- `ui` owns presentation-only views and templates.

## Runtime Config Boundary

- `WorkflowRuntimeConfig` is the normalized representation of `Workflow.definition_payload` in the application service layer.
- `GraphRuntimeConfig` is the execution-plane config consumed by `GraphRuntime` and lives in `graphs/config.py`.
- `apps/automation/services/runtime.py` maps `WorkflowRuntimeConfig -> GraphRuntimeConfig` in one place during runtime assembly.
- `graphs/runtime.py` consumes `GraphRuntimeConfig` only and does not import `apps/automation/services/workflow_config.py`.
- `workflow_config.py` stays focused on parse, normalization, and validation of workflow definition payloads.

## Configuration Boundary

- `settings` / environment variables hold secrets and deployment-level config.
- `Workflow.definition_payload` holds workflow-level config such as model choice, allowed tools, and graph behavior.
- `Workflow.definition_payload.graph.kind` selects the workflow graph. The current default and supported value is `llm_echo_summary`.
- Missing or empty `graph.kind` defaults to `llm_echo_summary` and is reported as a validation warning.
- Unknown `graph.kind` is a validation error.
- `llm_echo_summary` carries dependency metadata: `requires_llm = true` and `required_tools = ["echo"]`.
- `llm_echo_summary` requires `llm.enabled = true` and a non-empty `llm.model`.
- `llm_echo_summary` with `tools.allowed` missing `echo` is currently a validation warning so the policy-deny path remains observable.
- `Workflow.definition_payload.llm` is the minimal LLM schema.
- `Workflow.definition_payload.tools.allowed` is the minimal tool allowlist schema.
- Missing or empty `tools.allowed` means deny all.
- `Run.input_payload` holds one-shot execution input.
- `Run.input_payload` must not grant tool permissions.
- `Run.input_payload` must not provide LLM credentials.
- `Run.input_payload` must not provide `model`, `api_key`, `base_url`, `tools.allowed`, or `graph.kind`.
- `Run.output_payload` holds safe summary only.
- `RunEvent.payload`, `ExecutionSpan.metadata`, `ExecutionSpan.input_summary`, and `ExecutionSpan.output_summary` must not store secrets or raw provider payloads.
- runtime factory reads settings, `Workflow`, and `Run` context to assemble dependencies.
- execution-plane config is graph-local and must not carry API keys, base URLs, or raw `Run.input_payload`.

Reference diagnostic workflow minimal config:

```json
{
  "graph": {
    "kind": "llm_echo_summary"
  },
  "llm": {
    "enabled": true,
    "model": "test-model",
    "temperature": 0.2,
    "max_tokens": 512
  },
  "tools": {
    "allowed": ["echo"]
  }
}
```

Secret policy:

- secrets must not be stored in `Workflow.definition_payload`
- secrets must not be stored in `Run.input_payload`
- secrets must not be stored in `Run.output_payload`
- secrets must not be stored in `RunEvent.payload`
- secrets must not be stored in `ExecutionSpan.metadata`
- secrets must not be stored in `ExecutionSpan.input_summary`
- secrets must not be stored in `ExecutionSpan.output_summary`

## Graph Registry

- `graphs/registry.py` is the foundation registry mechanism.
- `GraphRegistry` stores `GraphDefinition` entries and dependency metadata.
- `DEFAULT_GRAPH_KIND` is `llm_echo_summary`.
- `workflows/catalog.py` composes the built-in workflow catalog and returns a registry instance.
- `supported_graph_kinds()` and `graph_requirements()` come from the composed registry instance.
- `build_graph()` does registry lookup only; it does not import concrete workflows or branch on `graph.kind` inline.

## Workflow Catalog

- `workflows/catalog.py` is the composition boundary for built-in workflow definitions.
- It collects reference workflows and will be the registration point for future application workflows.
- `graphs/registry.py` stays free of concrete workflow imports.

## Reference Diagnostic Workflow

- current implementation: `src/langgraph_automation/workflows/reference/llm_echo_summary/`
- default graph: `llm_echo_summary`
- positioning: reference / diagnostic / smoke-test workflow for runtime wiring
- input schema: `{"text": "..."}` or `{"prompt": "..."}`
- execution flow: `Run.input_payload` -> EchoTool node -> LLM summary node -> output candidate -> `services/runs.py` -> `safe_run_output_payload()` -> `Run.output_payload`
- `GraphRuntime.require_llm_client()` and `GraphRuntime.require_tool_registry()` are the only dependency access points inside nodes.
- nodes do not import Django ORM models, provider adapters, or concrete tool classes.
- `ObservedLLMClient` records LLM spans and `ObservedToolRegistry` records tool spans.
- full prompt, full response, and raw tool output are not persisted.
- `LLMResult.raw` is not persisted.

## Execution Input Boundary

- `Run.input_payload` is the user input source of truth.
- `GraphRuntime.execution_input` is transient execution input for nodes.
- graph state is checkpoint-safe and must not copy raw `Run.input_payload` wholesale.
- nodes should read input through `GraphRuntime.require_execution_input()`.
- graph state may retain `input_summary` and other bounded safe metadata.
- raw prompt, raw response, raw tool output, and secrets must stay out of checkpointable state.

## Failure Masking

- service-layer `run_failed()` observability calls are best-effort only.
- if `run_failed()` fails while handling a primary execution failure, the primary failure is preserved.
- observability failures in failure paths are suppressed and logged as warnings through the shared failure policy helper.

## Current Graph

- The reference diagnostic graph is the minimal `llm_echo_summary` LangGraph flow.
- `graphs/builders.py` builds and compiles the graph from the registry.
- `graphs/runner.py` invokes the compiled graph.
- `graphs/instrumentation.py` manages node span lifecycle.
- workflow-specific nodes live in `workflows/reference/llm_echo_summary`; foundation helpers in `graphs/nodes` do not own concrete workflow logic.

## Runtime Dependency Policy

- `GraphRuntime` is the dependency bundle passed into graph nodes.
- `LLMClient` and `ToolRegistry` are optional runtime dependencies.
- nodes that need them must call `require_llm_client()` / `require_tool_registry()`.
- missing dependencies fail fast with `MissingRuntimeDependencyError`.
- placeholder clients are not injected when a dependency is absent.
- `ObservedLLMClient` exists as the decorator layer for real LLM adapters, and the runtime factory currently wires it around `LiteLLMClient` when LLM is enabled.
- `ObservedToolRegistry` exists as the decorator layer for real tool registries, and the runtime factory currently wires it around the safe echo tool stack.

## Tool Policy Foundation

Tool execution permission is a separate policy layer from concrete tool execution and observability.

Wrapper order:

- `ConcreteToolRegistry`
- `PolicyAwareToolRegistry`
- `ObservedToolRegistry`

Responsibilities:

- `ConcreteToolRegistry` owns tool registration, lookup, and execution.
- `PolicyAwareToolRegistry` owns authorization and deny-result generation. It does not know about EventSink, Django, or graph execution.
- `ObservedToolRegistry` owns span recording for allowed, denied, failed, and exceptional tool outcomes. It does not know policy internals.

Policy deny behavior:

- policy deny is represented as a failed `ToolResult`
- policy deny does not raise by default
- policy evaluation exceptions are propagated
- deny metadata must not contain raw kwargs or secrets

Policy configuration vs execution metadata:

- `AllowlistToolPolicy` owns `allowed_tools`
- `ToolPolicyContext` carries execution metadata only (`run_id`, `workflow_id`, `thread_id`)

Workflow tool allowlist schema:

```json
{
  "tools": {
    "allowed": ["echo"]
  }
}
```

Configuration boundary:

- `Workflow.definition_payload` may define allowed tools
- the runtime factory should parse workflow config and build pure policy data
- policy objects receive pure data only
- `Run.input_payload` must not grant tool permissions

Current built-in safe tool:

- `echo` -> safe bounded preview echo tool
- no shell / file / network access
- output is redacted and bounded

Future TODO:

- strict `Workflow` validation for `tools.allowed`
- add shell/file/network policy types
- add filesystem path policy
- add network domain policy

## Boundary Contracts

- LangGraph nodes return state patch dicts.
- Graph state is checkpoint-safe and only carries summaries, metadata, and bounded execution markers.
- The runner returns an output candidate to the service layer.
- The service layer normalizes that candidate with `safe_run_output_payload()` before persisting `Run.output_payload`.
- `Run.output_payload` is the safe summary intended for UI/API display.
- Graph state, output candidates, and `Run.output_payload` must not contain raw `input_payload`, full prompts/messages, full raw LLM responses, `LLMResult.raw`, raw `ToolResult.output`, provider raw objects, `api_key`, tokens, authorization headers, passwords, absolute local file paths, or full tracebacks.

## Boundary Plan

- `graphs/` is the execution foundation layer.
- `graphs/registry.py` is the registry mechanism only.
- `workflows/catalog.py` composes built-in workflow definitions.
- `llm_echo_summary` is a reference diagnostic workflow used to verify wiring.
- planner / reviewer / executor workflows are future application workflows and should live outside the foundation package.
- `workflows/reference/` and `workflows/applications/` are the future split points for concrete workflow code.
