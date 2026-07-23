# Architecture

## Layers

- `api`: public facade and engine composition entry point
- `workflows`: definitions, requirements, preparation, execution adapter, and built-in catalog
- `runtime`: provider/tool/store/event-sink assembly
- `integrations`: concrete external-system adapters
- `apps/automation`: Django control plane and Run lifecycle
- `apps/web`: presentation and dynamic UI rendering
- `core`: safety, redaction, summaries, and shared errors

LangGraph is not a package layer. A workflow may use LangGraph internally, as `reference.llm_echo_summary` does, without exposing graph-specific types to the engine or control plane.

## Dependency Direction

- public workflows depend on `api.*` contracts
- runtime assembly depends on validated config and plugin contributions
- the control plane depends on `api.engine` and framework-neutral execution results
- workflows do not depend on Django models or control-plane services
- concrete integrations do not define package architecture

## Internal Loose Coupling

Loose coupling applies inside the package, not only at the public boundary. Workflow selection, dependency assembly, execution, persistence, observability, and UI projection have separate owners. A new workflow should normally require only a new contribution and tests, not edits to engine, runtime assembly, Run orchestration, or UI renderer internals.

## Workflow Execution Boundary

Every Run requires a valid `WorkflowReference`. `DeploymentEngineOwner` prepares an `EnginePreparedWorkflow`, and the control plane executes it through the public executable adapter. There is no graph registry, graph runtime, graph runner, or fallback path.

`WorkflowExecutionContext` supplies per-run identity and observability context. `WorkflowExecutionResult` is converted to `ControlPlaneExecutionResult`, after which the Run service owns safe output/error persistence and lifecycle transitions.

## Plugin And Runtime Boundary

- `api.plugins` contains declarative plugin vocabulary
- `PluginRegistry` stores contributions, not concrete runtime dependencies
- `ConfigValidator` invokes validation hooks
- `RuntimeAssembler` constructs initialized capabilities
- `WorkflowBuildContext` exposes only declared initialized capabilities
- secrets and factory contexts do not cross into workflow code

## Dynamic UI Boundary

Dynamic UI is a metadata projection and rendering concern. It must not instantiate providers, tools, stores, workflows, or secrets. Rendered values use safe model projections and bounded summaries.

## Persistence Convergence

Artifact and checkpoint stores are public storage capabilities. Memory backends are `EPHEMERAL`; filesystem backends are `PROCESS_DURABLE`. Storage durability is distinct from execution persistence and true resume. LangGraph `BaseCheckpointSaver` integration and resume semantics remain deferred until one explicit convergence contract is approved.

## Safety

- `Run.output_payload` is written only through `safe_run_output_payload`
- `Run.error_message` is written only through `safe_run_error_message`
- raw provider payloads, tool output, secrets, absolute paths, and tracebacks do not cross safe persistence boundaries
- secondary observability failures do not replace primary failures
