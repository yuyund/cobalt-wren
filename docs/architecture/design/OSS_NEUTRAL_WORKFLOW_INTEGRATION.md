---
type: design
status: proposed
authority: normative-direction
summary: OSS-neutral workflow integrations, dynamic control-plane projection, common operations, persistence, and native authoring boundaries.
verified:
  date: 2026-07-24
  commit: WORKTREE
  method:
    - architecture-discussion-sync
---
# OSS-Neutral Workflow Integration And Control Plane

## Product Value

The package's primary value is:

1. common operational control across workflow implementations; and
2. neutrality toward the workflow OSS or custom runtime that implements a workflow.

Neutrality does not mean reducing every integration to the smallest common set of fields. It means the foundation does not encode framework-specific branches, while integration helpers preserve and project as much useful framework information as stable public hooks allow.

The control plane must be more useful than opening each framework UI independently. Its distinct value is cross-framework correlation, consistent operations, audit, policy, business semantics, safe retention, and one composable operational view.

## Current Execution Boundary

A workflow contribution returns an opaque executable object. The generic execution adapter uses capabilities rather than framework identity:

1. `execute(...)` when available;
2. otherwise `invoke(...)`;
3. otherwise a callable;
4. optional `resume(...)` for resumable executables.

The foundation does not infer graph nodes, edges, state schemas, interrupts, checkpoints, tools, or LLM calls from an arbitrary compiled object. A LangGraph compiled graph works because it exposes a compatible public invocation capability, not because the foundation parses LangGraph internals.

Connection remains the external workflow package's responsibility. The scaffold and future integration helpers reduce that connection code, but a compiled object alone is not plugin discovery, workflow registration, or rich observability.

## Integration Architecture

The generic adapter remains framework-neutral and unchanged by individual OSS support.

```text
external OSS object
    -> integration helper
    -> public workflow contract
    -> generic capability adapter
    -> control plane
```

An integration helper is a semantic adapter, not only a call wrapper. It may own:

- contribution and definition construction;
- execution and result normalization;
- framework configuration derived from `WorkflowExecutionContext`;
- lifecycle and observability extraction;
- node, task, activity, agent, event, or subflow projection;
- cancellation, retry, waiting, resume, and checkpoint bridging where supported;
- diagnostics and compatibility warnings;
- renderer-neutral presentation contributions.

The foundation must never contain logic such as `if integration == "langgraph"`. It understands only registered contracts, opaque integration IDs, canonical records, schema identifiers, action descriptors, and renderer-neutral view specifications.

## Integration Definitions And Discovery

Integration implementation code is distributed with this package. The supported OSS distributions themselves are not mandatory dependencies. Availability is detected from the user's environment.

Support metadata is centrally declared rather than scattered through integration modules as ad hoc `try import` blocks. An integration definition should describe at least:

- opaque integration ID;
- target distribution and import name;
- provider implementation path;
- supported version range;
- maturity status;
- detection priority;
- declared capabilities;
- known limitations;
- documentation reference;
- whether automatic detection is eligible.

The registry owns lazy loading, availability checks, version compatibility, diagnostics, and capability publication. Explicit integration selection remains the reliable foundation path. Automatic inference, decorators, and zero-config conveniences belong to a separate convenience layer so inference policy does not become a foundation contract.

## Integration Depth

"Supported" must not imply identical depth. Integrations expose verified capabilities, for example:

- executable: run lifecycle, input/output summaries, terminal result;
- observable: execution hierarchy, attempts, framework events, metrics, artifacts, diagnostics;
- managed: cancel, retry, waiting, resume, checkpoints, durable recovery where semantically valid.

Capabilities must be proven through reusable contract scenarios rather than declared optimistically. UI actions are generated from current descriptors and capabilities; unsupported operations are absent or explicitly described as unavailable.

The goal for official integrations is not merely executable-level support. Helpers should use official callbacks, hooks, listeners, streams, event APIs, and inspection APIs to maximize useful projection. Private attributes and unrestricted object dumps are not acceptable integration mechanisms.

## Common Semantics Without Information Loss

The foundation uses a small canonical vocabulary as connective tissue:

- Run;
- ExecutionUnit and parent-child relationships;
- lifecycle transition;
- Interaction;
- Action and ActionAttempt;
- ArtifactReference;
- CheckpointReference;
- Metric;
- Diagnostic;
- correlation, subject, time, status, and attempt identity.

Framework concepts map into semantic kinds without erasing their origin. Examples include a graph node, task run, activity, agent, routed event, signal, timer, or child workflow. Each record may carry both a cross-framework semantic kind and an opaque integration-specific kind.

The canonical layer exists for search, correlation, policy, audit, actions, and lifecycle reasoning. It is not the maximum information model and must not limit what can be displayed.

## Dynamic Presentation

The UI is composed from common operational semantics and integration-provided sections. It should not present a low-information "common tab" beside a richer "framework tab". Both are projected into one coherent Run and execution-unit experience.

The common contribution must provide value that framework-native UIs generally cannot provide alone:

- one business Run spanning multiple workflow engines;
- cross-framework trace and relationship views;
- consistent action and approval surfaces;
- common audit and policy enforcement;
- SLA, ownership, subject, and business-operation semantics;
- organization-wide search and diagnostics;
- safe artifact, checkpoint, and retained-payload access.

Integration helpers may register renderer-neutral sections using foundation-owned block types such as facts, table, timeline, tree, graph, metric, diff, bounded JSON inspection, status banner, and action form. They must not register arbitrary HTML, templates, CSS classes, React code, or executable UI logic.

The renderer owns security, permission checks, redaction, bounding, accessibility, theming, and backwards compatibility. Deep engine debugging may link to an OSS-native UI when that UI provides capabilities the control plane should not duplicate.

## Persistence Model

Persistence is divided into three layers.

### Canonical control-plane records

Fixed, indexed records hold the state required for common operations, lifecycle, correlation, policy, audit, and search. These include Run, ExecutionUnit, lifecycle events, interactions, action descriptors and attempts, artifact references, checkpoint references, metrics, diagnostics, parent-child links, timestamps, attempts, subjects, and correlation IDs.

### Semantic attributes

Bounded, redacted, JSON-safe attributes hold information useful across multiple integrations but not universal enough for fixed columns. Namespaces, schema versions, indexable keys, and size limits are required.

### Integration projections

Framework-specific details are stored as versioned projection payloads attached to canonical owners. The foundation treats the schema ID and payload as opaque except for validation, redaction classification, retention, ownership, and size constraints. The responsible integration supplies interpretation and presentation.

Do not persist Python pickles, compiled graphs, framework handles, private object dumps, or an unbounded copy of framework event history. Store stable projections extracted from public APIs.

Canonical lifecycle events should be append-only. Current-state records may be updated for efficient reads. This is a pragmatic event-history plus materialized-state model, not a requirement for complete event sourcing.

## Checkpoints And Artifacts

Checkpoint ownership is explicit:

- foundation-managed: the foundation stores and interprets the native checkpoint schema;
- integration-managed: the integration owns the checkpoint body and the foundation retains a safe reference and action route;
- external: another service owns it and the foundation stores only the verified external reference and metadata.

Storage durability does not imply execution resume. Integration-specific checkpoint semantics, identity, replay, pending writes, serializer rules, and migration remain owned by the integration unless deliberately converged with a foundation contract.

Large artifact bodies belong in an artifact backend. Control-plane rows store identity, storage key or URI, content type, size, checksum, classification, retention, producer, and safe preview metadata. Small bounded JSON values may be inline only under an explicit policy.

## Safety And Retention

All integration data passes through:

```text
helper extraction
    -> schema validation
    -> redaction
    -> size and depth bounding
    -> classification
    -> persistence
```

The foundation owns the final safety boundary even when an integration claims its data is safe. Raw prompts, provider responses, tool outputs, credentials, tracebacks, filesystem paths, or business payloads must not be retained without explicit safe projection rules.

Retention is data-class and schema specific. Canonical lifecycle and action audit records may be long lived; detailed diagnostics, framework events, fine-grained metric samples, and large projections should normally expire earlier. Schema definitions should declare maximum payload size, retention class, searchable fields, and redaction classification.

## Native Authoring

Two different simplification goals must remain separate:

1. simplifying connection of an externally implemented workflow to the foundation; and
2. simplifying implementation of the workflow itself.

The first is integration and convenience UX. The second is a distinct native authoring product.

Native Authoring is now directionally defined as an async-first Python workflow model with ordinary control flow and explicit named step boundaries. The initial target is bounded business pipelines using synchronous or asynchronous callables, branching, bounded loops, retry, timeout, cooperative cancellation, providers, tools, artifacts, progress, metrics, and automatic step observability. Durable waiting and resume are not part of the MVP.

Native authoring is treated as another integration. It receives no private persistence path, UI path, or control-plane feature unavailable through the integration contracts. New native features must be reviewed for whether they are general operational semantics, portable integration semantics, or isolated native extensions.

LangGraph is not the Native MVP backend. Native uses a plain Python execution model because its product promise is familiar control flow plus operational step boundaries, not durable graph execution. LangGraph remains the recommended integration for checkpoint recovery, interrupt/resume, durable waiting, time travel, graph cycles, stateful subgraphs, and agent memory. The two products share the common control plane but make different execution promises.

The complete use-case boundary and provisional API are defined in `docs/workflows/authoring/NATIVE_AUTHORING_USE_CASE_DESIGN.md`.

## Native Examples

The built-in workflow catalog is empty. Example workflows live outside the foundation catalog and carry no product compatibility promise. Explicit test plugins, external distributions, and official integration contract tests provide plain Python, Native, LangGraph, and LlamaIndex integration evidence.

## Validation Strategy

Neutrality must be demonstrated with vertically complete scenarios across materially different implementations. At minimum, run equivalent scenarios through a generic Python workflow and an official OSS integration; add a stateful/resumable integration before claiming managed neutrality.

Scenarios should cover:

- start, success, and failure;
- execution hierarchy and attempts;
- structured diagnostics;
- artifact emission;
- cancellation or retry;
- waiting and resume where supported;
- checkpoint ownership and restart behavior;
- action audit;
- dynamic UI composition;
- no framework-specific branching in foundation code.

Native authoring should be implemented only after these common integration and projection contracts are credible enough that native cannot define the control plane unilaterally.

## Implemented Foundation And LangGraph Integration

The first integration foundation block is implemented. `api.integrations` defines provisional framework-neutral capability, availability, projection, action, and provider contracts. The internal workflow integration registry supports centrally declared definitions, environment availability and version checks, lazy provider loading, and explicit provider resolution. Automatic inference remains deferred.

The first official provider is the experimental LangGraph integration. It uses LangGraph's public `stream(..., stream_mode=["debug", "values"])` and `Command(resume=...)` APIs. It projects task start, completion, failure, and interrupt information into existing node spans and normalized workflow results without inspecting compiled graph private attributes. Checkpoint storage and lineage remain owned by the workflow or LangGraph backend.

External packages can use the thin helper:

```python
from cobalt_wren.integrations.langgraph import integrate_langgraph

def build_workflow(context):
    graph = build_graph().compile(name=context.workflow_kind)
    return integrate_langgraph(
        graph,
        workflow_kind=context.workflow_kind,
        output_key="output_payload",
    )
```

The LangGraph scaffold generates this helper path. Target workflow frameworks are dependencies of the consuming workflow distribution, not Cobalt Wren extras. Provider implementations remain lazy so foundation imports, the empty built-in catalog, and Native examples work when neither target OSS is installed.

## Implemented Integration Projection Persistence And UI Composition

The control plane now persists integration-specific details through an append-only `IntegrationProjectionRecord`. Each record is attached to a canonical Run and may also be attached to an ExecutionSpan. The record stores an opaque integration ID, versioned schema ID, owner kind and external identity, renderer title, bounded JSON payload, retention class, classification, truncation metadata, and expiry. The foundation persistence and rendering code contains no workflow-framework imports or framework-name branches.

Projection payloads pass through the same bounded diagnostic safety pipeline used by retained diagnostic snapshots. Sensitive keys are redacted, non-JSON objects are converted safely, depth/item/text/byte limits are enforced, and retention is selected by data class. The initial retention classes are transient, diagnostic, execution detail, and audit.

`IntegrationProjectionSink` is a separate optional protocol rather than an expansion of the required `EventSink` contract. `DjangoEventSink` implements it, while integrations discover the callback structurally and suppress projection failures as secondary observability failures.

The experimental LangGraph provider currently emits:

- `langgraph.task.v1` for task start and terminal/waiting state;
- `langgraph.interrupt.v1` for bounded interrupt identity and value summaries;
- `langgraph.checkpoint_ref.v1` for public debug-stream checkpoint references, parent checkpoint identity, next nodes, task count, and source.

Checkpoint projections appear only when the compiled LangGraph object has a checkpointer and emits public checkpoint debug events. The control plane stores references and summaries; it does not interpret or copy the LangGraph checkpoint body.

Run and ExecutionSpan detail pages now compose active integration projections as generic renderer-owned structured sections. The renderer reads only the title, integration ID, schema ID, owner metadata, classification, truncation state, and safe payload. It has no LangGraph-specific template or conditional. This implements the first vertical proof that framework detail can remain rich without making the foundation framework-aware.

## Implemented Common Integration Action Routing

The control plane now supports framework-neutral action descriptors through the shared `integration.actions.v1` projection schema. Integrations may publish bounded action data containing action identity, target kind, label, safety, availability, input schema, fixed payload, and opaque metadata. The common UI router renders these descriptors without importing or branching on a workflow framework.

Action projections are presentation snapshots, not execution authority. On submission the server revalidates the Run state, projection expiry and ownership, descriptor availability, supported action type, and the newly prepared executable's current resume capability. Only then is the action routed through the existing `dispatch_resume` path. This preserves the same inline/worker execution modes, Run lifecycle handling, execution control, and safe result normalization used by existing workflow actions.

The first producer is the experimental LangGraph integration. When an interrupt pauses a graph, it emits a common Resume descriptor with a bounded resume-value field and the latest public checkpoint reference when available. The action router does not inspect `langgraph.interrupt.v1` or call `Command` directly; the prepared integration executable remains responsible for translating `WorkflowResumeRequest` into LangGraph semantics.

Dynamic action requests continue through the existing permission and audit boundary. Integration action names map to the common `resume_run` permission, request payloads are stored only as safe audit summaries, and worker-mode requests are queued as ordinary `ExecutionJobOperation.RESUME` jobs.

## Implemented Second OSS Integration: LlamaIndex Workflows

The second official experimental provider targets `llama-index-workflows` 2.22.x through the optional `llamaindex` package extra. It uses the public `Workflow.run()`, awaitable `WorkflowHandler`, `stream_events(expose_internal=True)`, and `StepStateChanged` APIs. It does not inspect workflow, handler, context, or runtime private attributes.

The provider normalizes the async, event-driven model into the same foundation contracts used by LangGraph:

- step runs become canonical ExecutionSpans with `span_type="step"`;
- `llamaindex.step.v1` records step state, worker identity, input event, and output event;
- `llamaindex.event.v1` records bounded summaries of public streamed events;
- terminal workflow results become `WorkflowExecutionResult`;
- permanent step failures close the matching span as failed and preserve the primary workflow exception.

LlamaIndex Workflows emits `NOT_RUNNING` before `WorkflowFailedEvent` for a failed step. The provider therefore delays terminal success classification until the event stream confirms whether a failure event follows. This prevents failed steps from being recorded as successful due to event ordering.

Because Workflows executes inside an asyncio loop while the current Django event sink is synchronous, the provider buffers span and projection operations during async execution and replays them synchronously after the handler completes or fails. This keeps framework integration code independent of Django while respecting Django's async-safety boundary.

Current capability depth is observable, not managed. Execute and step observability are supported; event observability and dynamic views are partial; waiting, resume, checkpoint management, external event injection, and common cancellation actions are not yet implemented. Runtime durability and replay remain owned by the selected LlamaIndex Workflows runtime.

This second vertical integration demonstrates that the common persistence and UI contracts are not limited to graph nodes or checkpoint-driven execution. The same Run, ExecutionSpan, versioned projection, safe persistence, and generic detail renderer support an event-driven step framework without foundation framework branches.

## Implemented Projection Semantics, Current State, And Timeline

Integration projection records now distinguish storage ownership from semantic subject identity. Each record carries a projection kind (`snapshot`, `event`, `reference`, or `action`), subject kind, stable subject external ID, sequence, and occurrence timestamp in addition to the existing canonical owner relationship. Existing records are backfilled from schema and safe payload fields without importing an OSS framework.

Providers emit execution-unit lifecycle records as append-only snapshots with stable node or step subjects. LlamaIndex streamed events remain events, LangGraph checkpoint records are references, and common action descriptors are actions. A failed LlamaIndex step emits a final failed snapshot after `WorkflowFailedEvent`, so current state cannot remain incorrectly successful.

The UI now derives three layers from the same active records:

- Current integration state selects only the latest snapshot for each integration, subject kind, subject identity, and schema.
- Integration timeline orders snapshot transitions and events by occurrence time, sequence, and record identity.
- Technical projections retain every versioned raw record in a collapsed diagnostic section.

The foundation performs this composition from semantic fields only and contains no LangGraph or LlamaIndex branch.

## Implemented Clean-Room External Plugin Distribution Proof

A separately installable `oss-integration-workflows` distribution now proves the packaging and discovery boundary for both official OSS helpers. The external wheel contributes `external.oss.langgraph` and `external.oss.llamaindex` through the public `cobalt_wren.plugins` entry-point group. Its foundation imports are limited to the public plugin/workflow vocabulary and the two public integration helpers.

The clean-room integration test builds the foundation and external package as wheels, installs them into a fresh virtual environment, discovers the external entry point through installed distribution metadata, migrates an isolated SQLite control-plane database, and executes both contributed workflows without explicit plugin injection. It then verifies canonical spans, framework projections, current-state composition, integration timeline composition, integration summary composition, and successful Run-detail HTML rendering.

This proof is intentionally stronger than the earlier in-process plugin fixtures: workflow resolution comes from installed entry-point metadata, the external package has independent project metadata and dependency declarations, and execution starts from database-backed Workflow and Run records. The test environment reuses the host dependency set through Python's system-site mechanism to avoid downloading the full dependency graph; wheel identity, entry-point loading, package imports, migration, execution, persistence, and UI rendering still occur from the fresh environment.

## Bundled Integrations Use The Same Boundary

The Native authoring implementation ships in the foundation distribution, but the foundation does not execute it as a privileged built-in. A Native authoring object is wrapped by the centrally registered `native` integration provider and becomes an opaque executable. Generic preparation and control-plane execution remain unaware of whether the executable originated from Native, LangGraph, LlamaIndex Workflows, plain Python, or an external plugin.

This rule also applies to future built-in examples or recipes: package co-location must not justify framework imports, integration-ID branches, private persistence, or dedicated UI composition in the foundation path.

## Implemented Optional Workflow OSS Dependency Boundary

The base project dependencies no longer include LangGraph. Optional extras are now `langgraph`, `llamaindex`, and `oss-integrations`. Integration definitions and helper facades remain importable without loading target framework modules; concrete providers are loaded only after explicit integration resolution. Architecture tests install an import blocker for `langgraph` and verify that the engine facade, built-in catalog, and reference executable still import and initialize.

## Implemented Integration Availability And Health UI

The control plane now exposes `/ui/integrations/` and per-integration detail pages built from central integration definitions and registry inspection. The renderer-neutral health specification includes distribution identity, installed and supported versions, maturity, availability, provider load health, optional installation extra, auto-detection eligibility, capabilities, and declared limitations.

Health inspection separates target availability from provider loading. Missing and incompatible targets are reported without importing provider modules. Available targets are resolved to verify provider loadability and definition compatibility. Provider failures are converted to fixed safe diagnostics; exception text, traceback, provider paths, and causes are not rendered. The UI uses a combined health status such as `ready`, `not_installed`, `version_incompatible`, `load_failed`, `invalid`, or `definition_mismatch`.

The UI is definition-driven and contains no LangGraph or LlamaIndex condition. Installation commands are derived from opaque `install_requirement` or `required_distribution` metadata declared by each central definition. Cobalt Wren does not synthesize package extras.

## Decisions And Open Questions

Decided direction:

- generic capability adapter remains framework-neutral;
- OSS-specific helpers live outside the generic adapter;
- integration code ships in the package while OSS distributions are detected from the environment;
- support metadata is centrally defined;
- explicit selection and automatic inference are separate layers;
- common UI and framework detail are dynamically composed, not split into duplicate experiences;
- canonical records and versioned integration projections coexist;
- native authoring is separate from external workflow connection and is treated as an integration.

Open questions:

- exact public integration-provider and projection schemas;
- supported-OSS manifest format and compatibility policy;
- first official integrations and required support depth;
- exact Native retry, timeout, concurrency, and subworkflow API details;
- which framework events remain references versus retained projections;
- renderer-neutral block vocabulary and extension compatibility rules.
