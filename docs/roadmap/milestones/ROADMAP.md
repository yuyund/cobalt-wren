# Roadmap

## 1. Roadmap Premises

This repository is building a foundation for LangGraph execution, not an application workflow product.

The current priority is to keep the execution foundation stable, keep reference workflows isolated, and avoid mixing future application logic into the core packages.

## 2. Foundation Roadmap

Foundation work is the execution substrate shared by multiple workflows.

### Foundation MVP

- workflow を catalog / registry に追加できる
- workflow-specific graph / nodes / state を foundation から分離できる
- GraphRuntime 経由で LLM / tool / artifact / checkpoint / observability を使える
- tool policy が workflow 単位で効く
- raw input / secret / provider raw object / traceback が永続化されない
- EventSink failure が primary failure を上書きしない
- architecture guard が境界違反を検出できる
- application workflow readiness gate を通せる

### Foundation Complete

- registry composition boundary が安定している
- reference workflow が foundation から隔離されている
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
- Keep reference workflows diagnostic.
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
- durable backend: deferred
- next block: Durable Artifact / Checkpoint Backend Block V

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
- persistence durability: artifact complete / checkpoint deferred

Persistence durability audit:

- Block T: complete
- durable artifact backend: complete
- durable checkpoint backend: deferred
- next block: Persistence Contract Test Harness Block U

Persistence contract test harness:

- Block U: complete
- durable artifact backend: complete
- durable checkpoint backend: deferred
- next block: Durable Checkpoint Backend Block V

Package Complete+ future work:

- `run_workflow`
- `api.runtime`
- graph execution public API
- worker / queue / outbox
- true resume
- external plugin discovery
- entry point discovery
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
