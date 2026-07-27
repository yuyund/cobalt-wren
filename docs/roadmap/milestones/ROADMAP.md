# Roadmap

## 1. Roadmap Premises

This repository is building an OSS-neutral workflow execution and control-plane foundation, not a LangGraph-specific runtime or an application workflow product.

The current priority is to keep the execution foundation stable, keep examples and application workflows outside the foundation catalog, prove useful official OSS integrations, and avoid mixing future application logic into the core packages.

## 2. Foundation Roadmap

Foundation work is the execution substrate shared by multiple workflows.

### Foundation MVP

- workflow を catalog / registry に追加できる
- workflow-specific graph / nodes / state を foundation から分離できる
- WorkflowBuildContext / WorkflowExecutionContext 経由で LLM / tool / artifact / checkpoint / observability を使える
- tool policy が workflow 単位で効く
- raw input / secret / provider raw object / traceback が永続化されない
- EventSink failure が primary failure を上書きしない
- architecture guard が境界違反を検出できる
- application workflow readiness gate を通せる

### Foundation Complete

- registry composition boundary が安定している
- built-in workflow catalog が空で、examples/application workflows が foundation registration から隔離されている
- validation / runtime assembly / graph execution の責務境界が安定している
- boundary contracts が docs と tests で固定されている

## 3. Package Roadmap

Package work is a later step after foundation stabilization.

### Package MVP

- public API の最小面
- internal module と public module の分離
- config taxonomy
- manual plugin registration
- WorkflowPlugin API
- ToolPlugin API
- provider / store / observability の最小 extension point
- safety を config で無効化できない
- minimal docs / examples

### Package Complete

- public/internal API が安定している
- plugin registration と config validation の責務が分離されている
- extension point が workflow / tool / provider / store ごとに分離されている
- docs / ADR / examples が最小のまま維持されている

## 4. Application Roadmap Is Out of Scope

Application roadmap is intentionally not part of the current implementation plan.

The repository should remain ready for application workflows, but application features must not be built inside the execution foundation.

## 5. Current Position

Foundation Roadmap:

- C5 Workflow registry composition boundary
- 状態: 完了

Foundation D0:

- Stabilization checkpoint
- 状態: 完了

Next:

- Package P0-A Public / internal API surface design docs
- Package P0-B minimal public facade module
- 状態: 完了

Current:

- Package P1-A Config taxonomy docs
- 状態: 完了

- Package P1-B Config schema boundary design docs
- 状態: 完了

- Package P3-A Plugin taxonomy design docs
- 状態: 完了

- Package P3-B Manual plugin registration design docs
- 状態: 完了

- Package P3-C Plugin API shape design docs
- 状態: 完了

- Package P3-D Plugin API facade design docs
- 状態: 完了

- Error taxonomy design docs
- 状態: 完了

- api.errors minimal facade design docs
- 状態: 完了

- api.errors minimal facade implementation
- 状態: 完了

- Config Core Block B
- 状態: 完了

Current:

- Config Validation Block C
- ConfigValidator + EffectivePluginSet + registry lookup
- 状態: 完了

Current:

- Runtime Assembly Block D
- 状態: 完了

Current:

- Workflow Extension Block E
- api.workflow + WorkflowContribution support
- 状態: 完了

Current:

- Built-in Wiring Block F
- 状態: 完了

Current:

- Application Readiness Block G
- 状態: 完了

Current:

- Persistence Configuration Ownership Closure X1C2
- 状態: 完了

Current:

- Persistence Configuration Composition Proof X1C3
- 状態: 完了

After Block G:

- Package / Foundation MVP gate complete

## 6. Recommended Execution Order

1. Finish foundation boundary cleanup.
2. Stabilize contracts with docs and tests.
3. Move to stabilization checkpoint review.
4. Design the package public/internal API surface.
5. Only then consider application workflow layering.
6. Move to execution integration once readiness gates are documented.

## 7. Non-goals

- company_agent の本実装
- planner / reviewer / executor の本実装
- multi-agent orchestration の本実装
- customer-specific workflow の本実装
- application-specific UI の本実装

## 8. Design Principles

- Keep foundation generic.
- Keep examples non-product and explicitly registered.
- Keep application workflows out of the foundation package.
- Prefer registry/catalog composition over direct imports in foundation code.
- Prefer explicit boundary contracts over implicit conventions.
- Keep safety boundaries redaction-safe by default.

## 9. Package Completion And Beyond

Package / Foundation MVP:

- complete

Workflow preparation path:

- complete

Service workflow preparation bridge:

- complete and routed through `api.engine`

Package Roadmap Correction Block J:

- complete

Package Facade Design Block K:

- complete

Package Facade Implementation Block L:

- complete

Package Verification Harness Block M:

- complete

Boundary Hardening Block N:

- complete

Service Integration via Package Facade Block O:

- complete

## 10. System Assurance Roadmap

System Assurance Scope Expansion Audit Block Q:

- complete

Current:

- System P0 Assurance Gap Closure Block R
- 状態: 完了

Next:

- System P1 Safety Exposure Hardening Block S
- 状態: 完了

Next focus areas:

- persistence durability assurance and contract test harness
- control-plane execution facade follow-up

Persistence contract test harness:

- Block U: complete
- durable backend: complete
- next block: Checkpoint Backend Runtime Selection and Configuration Block W4

Artifact protocol sufficiency / durable backend design:

- Block V: complete
- protocol decision: APPROVED_FOR_IMPLEMENTATION
- selected backend candidate: FilesystemArtifactStore
- durability target: PROCESS_DURABLE
- next block: Filesystem Artifact Backend Implementation Block V3

Artifact Store Protocol Evolution Block V2:

- complete
- body-aware ArtifactStore contract: complete
- MemoryArtifactStore reference implementation: complete
- FilesystemArtifactStore implementation: complete

Artifact Backend Runtime Selection and Configuration Block V4:

- complete
- typed artifact store settings: complete
- canonical runtime builder: complete
- explicit filesystem opt-in: complete
- no fallback semantics: complete

Checkpoint Durability Contract and Protocol Sufficiency Audit Block W1:

- complete
- checkpoint protocol sufficiency audit: complete
- versioned execution state contract: approved
- next block: Checkpoint Store Protocol Evolution Block W2

Checkpoint Store Protocol Evolution Block W2:

- complete
- checkpoint store protocol: versioned / immutable / serializer-aware / conflict-aware
- MemoryCheckpointStore reference implementation: complete
- filesystem backend readiness: approved
- next block: Filesystem Checkpoint Backend Implementation Block W3

Filesystem Checkpoint Backend Implementation Block W3:

- complete
- FilesystemCheckpointStore implementation: complete
- process-durable filesystem checkpoint backend: complete
- filesystem checkpoint backend implementation: complete
- process-durable filesystem checkpoint backend: complete
- next block: Checkpoint Backend Runtime Selection and Configuration Block W4

Later:

- Minimal Application Workflow Example
- company_agent

Package Complete:

- complete

Application workflow:

- deferred

company_agent:

- deferred

P1 safety exposure hardening:

- admin/UI redaction assurance: complete
- observability metadata safety: complete
- artifact/store body safety: complete
- safe error exposure: complete
- persistence durability: artifact complete / checkpoint filesystem complete / checkpoint runtime selection complete

Persistence durability audit:

- Block T: complete
- durable artifact backend: complete
- durable checkpoint protocol: complete
- durable checkpoint backend: complete
- next block: Persistence Contract Test Harness Block U

Persistence contract test harness:

- Block U: complete
- durable artifact backend: complete
- durable checkpoint protocol: complete
- durable checkpoint backend: complete
- next block: Checkpoint Backend Runtime Selection and Configuration Block W4

Persistence Orchestration Sufficiency Audit X1:

- complete
- canonical execution path inventory: complete
- runtime dependency propagation audit: complete
- run lifecycle and transaction boundary audit: complete
- LangGraph adapter sufficiency audit: complete
- control-plane projection audit: complete
- next blocks sequenced: complete

Persistence Runtime Propagation Closure X1C:

- complete
- selected artifact/checkpoint stores now propagate into `WorkflowBuildContext`: complete
- direct concrete store construction in application runtime: removed
- next block: Artifact Emission and Identity Contract X2

Persistence Configuration Composition Proof X1C3:

- complete
- normalized package config bound once at application composition: complete
- per-run physical persistence override removed: complete
- next block: Artifact Emission and Identity Contract X2

Persistence Deployment Startup Proof X1C4:

- complete
- deployment-owned production config source: complete
- startup binding and fail-safe validation: complete
- next block: Artifact Emission and Identity Contract X2

Persistence Construction Timing Semantics X1C4A:

- complete
- backend constructor timing: complete
- normalized ready() equality: complete
- startup/runtime failure taxonomy: complete
- next block: Artifact Emission and Identity Contract X2

Artifact Emission and Identity Contract X2:

- status: complete
- explicit artifact emission only: complete
- deterministic logical identity: complete
- caller-owned serialization: complete
- required artifact failure policy: complete
- next block: artifact persistence orchestration implementation x4
- next block: Artifact Persistence Orchestration Implementation X4

Artifact Emission Contract Completeness Closure X2A:

- status: complete
- package-internal contract: complete
- execution-owned `run_id`: complete
- attempt exclusion: complete
- required-only policy: complete
- validation bounds and deterministic mapping: complete
- next block: artifact persistence orchestration implementation x4

Package Complete+ future work:

- `run_workflow`
- `api.runtime`
- graph execution public API
- worker / queue / outbox
- true resume
- plugin API version migration and compatibility matrix
- partial-startup policy for broken third-party entry points
- `company_agent`
- production application workflow

Before Package Complete+:

- application-facing package facade must stay stable
- verification harness must continue to cover package-facing entrypoints
- application/control-plane code must remain on the facade path
- package internals must stay hidden from application/control-plane code

Recommended order after Block O:

1. Minimal Application Workflow Example Block P
2. company_agent Block Q

Before First Application Workflow:

- package facade must be the preferred entrypoint
- service bridge must be routed through package facade
- existing safety tests must remain green
- no application workflow direct dependency on control plane

## 10. Package Assurance Audit

Current:

- Package Assurance Code-First Audit Block P
- 状態: 完了

Audit output:

- `../../package/gaps/PACKAGE_ASSURANCE_INVENTORY.md`
- `../../package/completion/PACKAGE_INVARIANTS.md`
- `../../package/verification/PACKAGE_TEST_TRACEABILITY.md`
- `../../package/gaps/PACKAGE_ASSURANCE_GAPS.md`
- `../../package/verification/PACKAGE_TEST_ROADMAP.md`

Next:

- First P0 Assurance Gap Closure Block

Audit focus:

- code-first evidence
- traceability
- risk-ranked gap closure
- docs/code/test reconciliation

## 11. OSS-Neutral Integration And Native Authoring Direction

Planned architectural sequence:

1. define an integration provider protocol and centrally managed supported-OSS definitions;
2. keep the generic `execute` / `invoke` / callable / `resume` adapter framework-neutral;
3. add official semantic helpers that maximize lifecycle, observability, managed actions, and dynamic presentation through public OSS hooks;
4. establish canonical control-plane records plus bounded versioned integration projections;
5. validate equivalent vertical scenarios across generic Python and materially different OSS integrations;
6. only then define a lightweight native authoring MVP on the same integration contracts.

Integration code will be packaged with the foundation while target OSS distributions remain optional and are detected from the deployment environment. Explicit integration selection remains the stable path; automatic detection belongs to a separate convenience layer.

The built-in workflow catalog is empty. Examples are explicitly registered outside the foundation catalog, and external distribution tests provide integration evidence. LangGraph is not the Native authoring backend; Native uses the selected plain-Python execution model.

See `../../architecture/design/OSS_NEUTRAL_WORKFLOW_INTEGRATION.md`.

## 12. Native Authoring Roadmap

Native Authoring is now use-case-defined rather than backend-defined. The selected direction is ordinary async-first Python control flow with explicit named step boundaries and a plain Python backend. LangGraph remains an optional advanced integration for durable stateful graph semantics.

Native Design Block NATIVE-D1:

- status: complete
- primary use cases and non-goals: defined
- progressive disclosure levels: defined
- LangGraph capability boundary: defined
- provisional public API: defined
- MVP acceptance scenarios: defined
- design artifact: `../../workflows/authoring/NATIVE_AUTHORING_USE_CASE_DESIGN.md`

Native block NATIVE-P1:

- status: complete
- provisional public Native vocabulary: complete
- async-first executor with sync callable support: complete
- named step spans and `native.step.v1` snapshots: complete
- cancellation checks: complete
- ordinary `WorkflowContribution` and plugin conversion: complete
- Django control-plane and common UI vertical proof: complete

Native block NATIVE-P2A:

- status: complete
- retry policy and attempt semantics: complete
- step timeout semantics: complete
- stable occurrence keys and bounded loop identity: complete
- Django retry persistence and timed-out Run proof: complete

Native examples separation:

- status: complete
- no product workflows are bundled or implicitly registered
- Native examples moved to `examples/native/`
- example workflow kinds carry no product compatibility promise
- engine and control-plane tests use explicit test plugins
- plain Python executable compatibility remains an independent contract

Next Native block, NATIVE-P2B:

1. artifact convenience API;
2. progress and metric projections;
3. clean-room external Native wheel proof;
4. reusable configured step definitions after the convenience APIs stabilize.

Native MVP explicitly excludes durable resume, timers, time travel, exactly-once guarantees, arbitrary distributed fan-out, and transparent mid-call process recovery.
