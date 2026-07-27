# Public API Inventory

This inventory is enforced by `tests/unit/architecture/test_public_api_surface.py`.
The source module's `__all__` is authoritative for exported symbols.

## Public facades

### `cobalt_wren.api.llm`

- `LLMClient`
- `LLMRequest`
- `LLMResult`

### `cobalt_wren.api.tools`

- `ToolRegistry`
- `ToolResult`
- `ToolPolicy`
- `ToolPolicyContext`
- `ToolPolicyDecision`

### `cobalt_wren.api.stores`

- `ArtifactStore`
- `ArtifactWriteRequest`
- `StoredArtifact`
- `ArtifactReadResult`
- `CheckpointStore`
- `CheckpointWriteRequest`
- `StoredCheckpoint`
- `CheckpointReadResult`

### `cobalt_wren.api.events`

- `EventSink`

### `cobalt_wren.api.errors`

- `FrameworkError`
- artifact and checkpoint error families
- plugin registration, resolution, and validation errors
- runtime assembly and workflow preparation errors
- execution, cancellation, timeout, and checkpoint compatibility errors
- `SafetyBoundaryError`

### `cobalt_wren.api.plugins`

- `DEFAULT_PLUGIN_ENTRY_POINT_GROUP`
- `PLUGIN_API_VERSION`
- `discover_plugins`
- `Plugin`
- `PluginMetadata`
- `PluginContributions`
- provider, tool, store, and event-sink contributions

### `cobalt_wren.api.workflow`

- workflow build and execution contexts
- execution control and resume request
- execution result and executable/resumable protocols
- workflow metadata, requirements, definition, and contribution

## Provisional facades

### `cobalt_wren.api.integrations`

Framework-neutral capability, availability, projection, action, context, and
provider SPI types.

### `cobalt_wren.api.engine`

- `EnginePreparedWorkflow`
- `AutomationEngine`
- `create_engine`

### `cobalt_wren.native`

- `NativeArtifact`
- `NativeWorkflowContext`
- `NativeWorkflow`
- `NativeExecutable`
- `RetryPolicy`
- `workflow`

## Stable identifiers

- plugin entry-point group: `cobalt_wren.plugins`
- plugin API version: exported as `PLUGIN_API_VERSION`
- Native integration ID: `native`
- current built-in projection schemas:
  - `native.step.v1`
  - `langgraph.task.v1`
  - `langgraph.interrupt.v1`
  - `langgraph.checkpoint_ref.v1`
  - `llamaindex.step.v1`
  - `llamaindex.event.v1`

## Intentionally not public

- package root re-exports
- concrete filesystem, PostgreSQL, S3, LiteLLM, LangGraph, and LlamaIndex implementations
- plugin registry
- config loader and runtime assembler
- Django models and services
- artifact emission orchestration internals
