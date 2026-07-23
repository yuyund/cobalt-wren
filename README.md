# LangGraph Automation

A workflow automation package with a Django control plane, a narrow public workflow/plugin API, replaceable runtime capabilities, and LangGraph as an optional workflow implementation detail.

The package is under active development and currently has no production consumers. Design rules are documented in `docs/architecture/design/DESIGN_PRINCIPLES.md` and `docs/architecture/design/DEVELOPMENT_COMPATIBILITY_POLICY.md`.

## Architecture

- `langgraph_automation.api`: public facades for workflows, plugins, providers, tools, stores, events, errors, and the engine.
- `workflows`: public-workflow preparation and built-in workflow composition.
- `runtime`: validated dependency assembly.
- `integrations`: concrete LLM, tool, artifact, checkpoint, and observability adapters.
- `apps/automation`: Django Run lifecycle, workflow reference parsing, engine ownership, safe persistence, and dynamic UI metadata.
- `core`: redaction, summaries, and result safety.

There is no production `graphs` package, graph registry, graph runtime, or graph runner. The built-in `reference.llm_echo_summary` workflow uses LangGraph only inside its `LlmEchoSummaryExecutable` implementation.

## Execution

A Django `Workflow` selects an executable through `definition_payload`:

```json
{
  "workflow": {
    "kind": "reference.llm_echo_summary",
    "config": {
      "allowed_tools": ["echo"]
    }
  }
}
```

Execution is one path:

```text
Run
→ WorkflowReference
→ DeploymentEngineOwner
→ EnginePreparedWorkflow
→ public executable
→ WorkflowExecutionResult
→ ControlPlaneExecutionResult
→ safe Run persistence
```

Missing, malformed, or unknown workflow references fail closed. There is no graph fallback.

## Runtime Configuration

Deployment configuration owns provider, tool, store, event-sink, and safety selection. Workflow configuration is opaque to the foundation and validated by the workflow contribution. `Run.input_payload` is execution input, not configuration and cannot grant capabilities or provide credentials.

The reference workflow requires the deployment to provide:

- provider profile `default`
- tool `echo`

Secrets are resolved by runtime assembly and are never exposed through `WorkflowBuildContext`.

## Observability

`WorkflowExecutionContext` carries per-run identity and observability context. The reference executable emits node spans and binds provider/tool spans to the node parent. Control-plane lifecycle emission follows `EnginePreparedWorkflow.lifecycle_events_owner`.

Observability failures are secondary and must not replace the primary execution result.

## Persistence

- Memory artifact and checkpoint stores are `EPHEMERAL` defaults.
- Filesystem artifact and checkpoint stores are `PROCESS_DURABLE` explicit opt-ins.
- Store durability does not imply execution resume.
- True resume and LangGraph `BaseCheckpointSaver` convergence remain deferred.

## Extension

External workflow distributions import only public `langgraph_automation.api.*` contracts. They may be explicitly registered or discovered through the optional `langgraph_automation.plugins` entry-point group.

See:

- `docs/index.md`
- `docs/workflows/authoring/WORKFLOW_AUTHOR_GUIDE.md`
- `docs/api/surface/API_SURFACE.md`
- `docs/contracts/core/CONTRACTS.md`
