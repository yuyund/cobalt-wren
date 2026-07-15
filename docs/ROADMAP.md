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

Next:

- Built-in Wiring Block F

## 6. Recommended Execution Order

1. Finish foundation boundary cleanup.
2. Stabilize contracts with docs and tests.
3. Move to stabilization checkpoint review.
4. Design the package public/internal API surface.
5. Only then consider application workflow layering.

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
