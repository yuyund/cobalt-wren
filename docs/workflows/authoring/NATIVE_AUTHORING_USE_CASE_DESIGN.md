---
type: design
status: proposed
authority: normative-direction
summary: Use-case-driven Native Authoring design, progressive disclosure, and explicit boundary with LangGraph.
verified:
  date: 2026-07-25
  commit: WORKTREE
  method:
    - use-case-first-design
    - langgraph-capability-comparison
---
# Native Authoring Use-Case Design

## Decision Summary

Native Authoring is not a reduced LangGraph implementation. It is the shortest supported path for writing ordinary Python workflows that need consistent execution boundaries, retry, timeout, cancellation, observability, artifacts, safe persistence, worker execution, and control-plane UI.

LangGraph remains the recommended integration when the workflow fundamentally requires durable stateful graph execution, checkpoint-based recovery, interrupt/resume, time travel, graph cycles, stateful subgraphs, or agent-oriented memory.

The product therefore exposes progressive levels of complexity rather than one universal authoring API:

1. recipes for common linear workflows;
2. Python workflows with explicit named step boundaries;
3. reusable step and subworkflow definitions;
4. advanced integration or external workflow engines.

The primary Native API is level 2. Recipes are convenience surfaces built on it. Advanced execution capabilities must not leak into the common path.

## User Experience Goal

A Python user should be able to retain ordinary Python control flow and ordinary typed functions while gaining operational behavior by marking only meaningful execution boundaries.

The intended experience is:

```python
@workflow(name="document-review")
async def document_review(ctx, request):
    document = await ctx.step("extract", extract_document, request)

    if document.sensitive:
        result = await ctx.step("manual-route", route_manual, document)
    else:
        result = await ctx.step("summarize", summarize, document)

    await ctx.step("publish", publish_result, result)
    return result
```

The user does not construct a graph, mutate shared framework state, declare edges, or implement observability wrappers. Ordinary `if`, `for`, `try`, function return values, and Python type annotations remain valid.

## Primary Use Cases

### Sequential business pipeline

Examples:

- validate input;
- call an external API;
- transform data;
- invoke an LLM;
- generate a report artifact;
- notify another system.

Native should make a three-to-ten-step pipeline concise and locally testable.

### Conditional business routing

A workflow may branch using ordinary Python conditions based on a prior step result. Each executed path is recorded dynamically. Predeclaring a complete DAG is not required.

### Bounded iteration

A workflow may process a bounded collection with an ordinary loop. Each meaningful item operation may become a named step. The runtime must enforce configurable limits on generated step identity count and name size.

### External API with retry and timeout

A user may attach retry and timeout policy to a step without wrapping the callable manually.

### LLM and tool workflow

The workflow may access declared providers and tools through a workflow context. Provider and tool raw objects must not become persisted output.

### Artifact-producing workflow

A step or workflow may write a report, JSON document, or binary artifact through an explicit artifact API and receive a safe descriptor.

### Failure and cancellation

A failure must identify the named step and attempt. Cancellation and deadline checks occur before steps and between retries, with an explicit user-callable check for long-running local logic.

### External package reuse

A Native workflow must convert to an ordinary `WorkflowContribution` and be publishable through the existing plugin entry-point mechanism. Native receives no private registration or execution path.

## Secondary Use Cases

These are expected after the first MVP but must fit the design without replacing it:

- reusable configured step definitions;
- bounded concurrency;
- subworkflows;
- partial collection failure;
- progress and custom metrics;
- result caching;
- idempotency metadata;
- compensation hooks;
- human approval through a later managed waiting contract.

## Explicit Non-Goals For MVP

Native MVP does not promise:

- checkpoint-based continuation from an arbitrary step;
- durable timers or multi-day waiting;
- deterministic replay of arbitrary Python;
- time travel or state fork;
- exactly-once side effects;
- distributed fan-out at arbitrary scale;
- event sourcing;
- dynamic DAG persistence;
- stateful subgraph memory;
- agent-loop semantics;
- transparent recovery from process death in the middle of a Python callable.

A user needing these semantics should select an integration designed for them, such as LangGraph for durable stateful graph execution.

## Capability Comparison With LangGraph

| Capability | Native MVP | LangGraph integration |
|---|---|---|
| Ordinary Python sequential flow | primary model | possible through graph nodes and edges |
| Python `if` and loop | direct | represented through routing, cycles, or node logic |
| Typed function input/output | primary model | commonly represented through shared graph state |
| Named observable execution unit | step | node/task |
| Retry | step policy | node/task/runtime mechanisms |
| Timeout | step policy | runtime-specific integration |
| Cooperative cancellation | before steps and between retries | between streamed task events in current integration |
| Artifact API | first-class foundation capability | application code uses foundation or external storage |
| Safe cross-framework UI | automatic | projected through integration helper |
| Checkpoint recovery | not in MVP | supported through LangGraph checkpointer |
| Interrupt/resume | not in MVP | supported and routed through common Resume action |
| Durable waiting | not in MVP | supported when backed by compatible persistence |
| Time travel and fork | not supported | LangGraph capability; foundation currently retains references only |
| Graph cycle and agent loop | not a core primitive | primary strength |
| Stateful subgraph | not in MVP | supported by LangGraph |
| Conversation and long-term memory | optional external capability later | established LangGraph patterns |
| Deep graph debugging | common step timeline only | LangGraph-native tooling recommended |

## Progressive Disclosure Model

### Level 1: Recipe

A recipe covers a common shape with minimal configuration.

```python
workflow = sequential_workflow(
    name="document-review",
    steps=(extract, classify, summarize),
)
```

Recipes must compile to the level-2 API. They must not introduce separate execution semantics.

### Level 2: Python workflow

This is the primary API.

```python
@workflow(name="document-review")
async def document_review(ctx, request):
    extracted = await ctx.step("extract", extract, request)
    return await ctx.step("summarize", summarize, extracted)
```

### Level 3: Reusable configured units

```python
fetch_customer = step(
    "fetch-customer",
    fetch_customer_record,
    retry=RetryPolicy(max_attempts=3),
    timeout_seconds=20,
)
```

The same definition may be used by multiple workflows.

### Level 4: Advanced integration

When the Native execution model is insufficient, users may return an external executable or use an official integration helper. This is an intentional escalation path, not a hidden fallback.

## Public API Shape

The provisional surface should be small:

```python
from cobalt_wren.native import (
    NativeWorkflowContext,
    RetryPolicy,
    step,
    workflow,
)
```

The `workflow` decorator attaches metadata and produces or can produce a `WorkflowContribution`. It does not inspect Python AST, infer a static DAG, rewrite control flow, or serialize local variables.

The context owns runtime behavior:

```python
result = await ctx.step(
    "fetch-customer",
    fetch_customer,
    customer_id,
    retry=RetryPolicy(max_attempts=3),
    timeout_seconds=20,
)
```

Step callables remain ordinary sync or async Python functions. A callable need not carry a decorator.

## Step Identity

A step call has:

- stable logical name supplied by the author;
- runtime occurrence identity assigned by the executor;
- attempt number;
- optional parent step or subworkflow identity;
- ordered sequence within the Run.

The logical name is used for current-state grouping only when repeated invocations represent the same logical subject. Iterative calls that represent different items require an explicit bounded key, for example `process-item:{item.safe_id}`. Raw payload values must not be embedded in step names.

Duplicate concurrent logical identities are rejected unless an explicit occurrence key is supplied.

## Retry Semantics

Retry belongs to a step execution boundary, not the workflow function as a whole.

A retry policy includes at least:

- maximum attempts;
- retryable exception types or predicate;
- fixed or exponential backoff;
- maximum delay;
- optional jitter policy;
- cancellation and deadline checks before every attempt and delay.

Each attempt receives a separate canonical Span or an explicit attempt child while the logical step snapshot remains stable. Primary exception semantics are preserved after the final attempt.

The runtime does not assume a step is idempotent. Documentation and later APIs may allow an idempotency key, but retry is an explicit author choice.

## Timeout Semantics

A step timeout bounds the awaited step execution. It does not guarantee termination of arbitrary synchronous code that ignores cancellation. Sync callables may require a worker thread or process strategy; the MVP must state which mechanism is implemented rather than claiming hard interruption.

Workflow-level deadline remains the existing `WorkflowExecutionControl` deadline. The effective step timeout is the smaller of the requested timeout and remaining workflow deadline.

## Sync And Async Boundary

The authoring model is async-first because external APIs, LLM providers, and tools are commonly asynchronous. Both sync and async callables are accepted.

The implementation must not invoke synchronous Django ORM operations from an async context implicitly. Application code remains responsible for using an appropriate adapter when touching ORM-bound services.

Local unit tests should be able to call step functions directly without a runtime.

## Context Capabilities

The Native context should expose narrowly scoped operations:

- `step(...)` and `run(step_definition, ...)`;
- `check_cancelled()`;
- `require_provider(name)`;
- `require_tool(name)`;
- artifact emission through a typed helper;
- progress and metric emission;
- safe workflow metadata such as Run and thread identity.

It must not expose Django models, internal registries, raw runtime dependencies, secret resolvers, or persistence implementation details.

## Observability And Projection

Every Native step automatically emits:

- canonical step Span;
- started and terminal snapshots using a stable subject identity;
- attempt and duration information;
- bounded input and output summaries;
- failure classification;
- progress and metric events when requested.

Native projection schemas are versioned and pass through the same persistence safety boundary as every other integration. Proposed initial schemas:

- `native.step.v1`;
- `native.progress.v1`;
- `native.metric.v1`.

The existing Current integration state, Integration timeline, Technical projections, and Integration Summary UI must render Native data without a Native-specific branch.

## Workflow Contribution Conversion

A decorated Native workflow must be convertible to an ordinary definition:

```python
contribution = document_review.contribution(
    kind="acme.document_review",
    requirements=WorkflowRequirements(
        provider_profiles=("default",),
        artifact_store=True,
    ),
)
```

The result participates in the same plugin registration, clean-room wheel distribution, engine preparation, generic execution adapter, Django Run lifecycle, and conformance suite as external workflows.

Native may provide convenience plugin construction, but the produced object must remain an ordinary public `Plugin` and `WorkflowContribution`.

## Local Testing Experience

A workflow package should support three test layers:

1. pure unit tests for ordinary step functions;
2. Native runner tests with an in-memory context and recording sink;
3. existing `WorkflowContractSuite` tests after contribution conversion.

Testing a pure function must not require Django, a worker, an event loop owned by the control plane, or integration registry discovery.

## Product Routing Guidance

Use Native when:

- execution lasts seconds to tens of minutes;
- flow is primarily business logic, API calls, LLM calls, tools, and artifacts;
- ordinary Python branching and bounded loops are desirable;
- retry and operational visibility are needed;
- restarting the whole workflow is acceptable after process failure.

Use LangGraph when:

- checkpoint-based crash recovery is required;
- execution must pause and resume after human or external input;
- state must persist across long waits;
- graph cycles or agent loops are central;
- time travel, fork, or stateful subgraphs are required;
- graph-specific streaming and debugging are important.

Use another integration when its event or domain model is the natural fit. Native must not be marketed as the only correct workflow model.

## MVP Acceptance Scenarios

The implementation is accepted only when all scenarios pass through the ordinary public path:

### Sequential LLM pipeline

Validate input, invoke a provider, and return a safe structured result.

### Conditional routing

Execute one of two named steps based on a typed prior result and show only the executed path in current state and timeline.

### Retrying external API

Fail twice with a retryable error, succeed on the third attempt, and expose attempt history without leaking exception internals.

### Loop and artifact report

Process a bounded set of items, generate stable occurrence identities, and write a report artifact.

### Failure and cancellation

Record the failed logical step, preserve the primary error, and stop before the next step when cancellation is requested.

### External distribution

Package a Native workflow in a separate wheel, discover it by entry point, execute through a database-backed Run, persist spans and projections, and render the common Run detail UI.

## Implementation Sequence

1. public provisional Native vocabulary and metadata;
2. async-first local executor with sync callable support;
3. named step execution and cancellation checks;
4. step spans and `native.step.v1` snapshots;
5. retry and timeout policies;
6. artifact, progress, and metric helpers;
7. contribution and plugin conversion;
8. unit, Django vertical, and clean-room distribution tests;
9. recipe layer only after the level-2 API proves stable;
10. reassess bounded concurrency and human approval separately.

## Built-In Integration Boundary

Native Authoring is bundled with the foundation distribution, but bundling does not grant it a private execution path. `NativeWorkflow` is an authoring object. During workflow build, it is passed through the official `native` integration provider and converted into an opaque executable in the same way that a LangGraph object is passed through the LangGraph provider.

The generic workflow preparer, adapter, engine facade, Django execution service, Run lifecycle, persistence services, and UI do not import Native Authoring or branch on the `native` integration ID. They receive only public workflow definitions and opaque executable capabilities. The distinction between a bundled workflow and an externally installed workflow affects registration and package availability only; it does not alter preparation, execution, observability, persistence, actions, or UI composition.

The central integration definition identifies the bundled target as `native`, with provider resolution, capabilities, maturity, limitations, and Health UI presentation handled through the same integration registry used by LangGraph and LlamaIndex Workflows.

## Implemented NATIVE-P1 Foundation

The first Native implementation block is complete. `cobalt_wren.native` now exposes a provisional `workflow` decorator, `NativeWorkflow`, `NativeWorkflowContext`, and `NativeExecutable`. A decorated workflow converts to ordinary public `WorkflowContribution` and `Plugin` objects. The generic workflow adapter and existing engine preparation path execute the resulting opaque executable without a Native-specific control-plane branch.

The executor is async-first. Workflow functions may be asynchronous, and explicit `ctx.step(...)` boundaries accept both async and sync callables. Sync step callables run through `asyncio.to_thread()` so they do not block the workflow event loop. Native execution currently enters through the package's synchronous workflow boundary; direct invocation from an already-running event loop is rejected explicitly rather than creating nested-loop behavior.

Each named step records a buffered lifecycle while the workflow coroutine runs. Buffering is required because the current Django EventSink is synchronous and may not safely access the ORM inside an asyncio context. After the coroutine completes or fails, operations replay synchronously into canonical `step` spans and `native.step.v1` snapshot projections. Running and terminal snapshots use the stable logical step name as the semantic subject, with deterministic sequence ordering.

Cancellation and deadline checks occur before each step and after the callable returns. A cancellation requested between steps prevents the next step from starting. Step failures preserve and re-raise the original exception to the execution boundary while retained span and projection diagnostics use a fixed safe message.

Implemented in this block:

- workflow metadata decorator without AST or control-flow rewriting;
- async workflow invocation;
- synchronous and asynchronous step callables;
- named step identity and ordered sequence;
- automatic canonical step spans;
- `native.step.v1` running, succeeded, and failed snapshots;
- cooperative cancellation and workflow deadline checks;
- provider, tool, and artifact-store lookup through public build context;
- ordinary `WorkflowContribution` and plugin conversion;
- Django Run, persistence, Current state, Timeline, Technical projections, and common UI vertical proof.

Still deferred from the MVP sequence:

- reusable configured step definitions;
- artifact convenience helpers;
- requirements-aware local validation and config suggestions;
- recipe layer.

## Native Examples Boundary

Native usage examples live under `examples/native/` and are not part of the built-in workflow catalog. They demonstrate the recommended authoring surface without creating stable product workflow kinds or implicit registration.

Examples may expose a `Plugin` value for copyability, but an application must register that plugin explicitly or publish it through the standard plugin entry-point group. The foundation currently ships no product workflows.

The lower-level plain Python executable SPI remains supported and is tested independently. Native is the recommended authoring experience; plain executable is the escape hatch.

## Implemented NATIVE-P2 Policy Core

The Native step boundary now supports explicit `RetryPolicy`, per-step `timeout_seconds`, and stable `occurrence_key` identity for bounded loops. These features remain inside the Native integration executable; the generic foundation execution path remains unchanged.

Retry creates a separate canonical step Span for every attempt. All attempts share one semantic occurrence identity. Projection snapshots use `running`, `retrying`, `succeeded`, or `failed`, include the attempt and maximum-attempt count, and preserve deterministic event sequence. Intermediate exception details are not retained. The original exception is re-raised after the final attempt.

`RetryPolicy` requires an explicit maximum attempt count, retryable exception types, and bounded fixed or exponential delay parameters. Cancellation and workflow deadline checks run before attempts, during retry delays, and after callables return. Retry remains an explicit author choice and does not imply idempotency.

Step timeout uses the smaller of the requested timeout and the remaining workflow deadline. Async callables are cancelled through the asyncio timeout boundary. Sync callables run in a worker thread; the awaiting workflow times out, but Python cannot guarantee forced termination of the underlying thread. This limitation is declared in the central Native integration capability. A terminal step timeout raises the existing `WorkflowTimeoutError`, so the common control plane records the Run as `timed_out`.

Repeated logical steps require a safe `occurrence_key`. The resulting semantic identity is `step-name:occurrence-key`. Keys are limited to 64 identifier characters and a workflow is limited to 1,000 step occurrences. Reusing an occurrence identity in one Run fails closed. This prevents raw business payloads and unbounded cardinality from becoming persisted execution identities.

## Deferred Decisions

- bounded concurrency API;
- subworkflow identity;
- cross-integration schema validation ownership;
- whether step decorators return callable wrappers or immutable definitions;
- whether Native is listed as a built-in integration in the Health UI before or after MVP completion.
