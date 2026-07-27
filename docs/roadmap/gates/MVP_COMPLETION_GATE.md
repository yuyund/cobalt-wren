# MVP Completion Gate

This document defines the completion gate for the package / foundation MVP.

## Package / Foundation MVP completion gate

The MVP gate is met when all of the following are in place:

- `api.errors` is implemented
- `api.plugins` is implemented
- `api.workflow` is implemented
- `PluginRegistry` is implemented
- `ConfigLoader` / normalizer are implemented
- `ConfigValidator` is implemented
- `EffectivePluginSet` is implemented
- `RuntimeAssembler` is implemented
- `RuntimeDependencies` is implemented
- built-in workflow contribution wiring is implemented
- workflow adapter is implemented
- workflow requirements checker is implemented
- application workflow readiness is documented
- architecture guards are in place
- tests are green

## What MVP complete means

MVP complete means:

- the foundation is ready to accept application workflows safely
- the main extension boundaries are stable
- examples can be explicitly registered without entering the built-in catalog

## What MVP complete does not mean

MVP complete does not mean:

- production-ready queue / resume / discovery exists
- `company_agent` is implemented
- production application workflows are implemented
- execution path migration is complete
- installed entry-point plugin discovery exists
- `api.runtime` exists as a public facade

## Not part of MVP

- worker / queue / outbox
- true resume
- external plugin discovery
- entry point discovery
- production application workflow
- `company_agent`
- `api.runtime` public facade
- full workflow execution integration

## Post-MVP Integration

- workflow preparation path is the first post-MVP execution integration step
- it prepares a workflow but does not execute it
- service layer integration remains future work

## Post-MVP Service Integration

- service layer bridge can prepare workflows through `WorkflowPreparer`
- service layer integration is post-MVP
- full execution path migration remains future work

## Package Complete

Package Complete means:

- application-facing package facade exists
- package facade hides `PluginRegistry`, `WorkflowPreparer`, `workflows.catalog`, `workflows.adapter`, `workflows.requirements`, `ConfigValidator`, and `RuntimeAssembler`
- application/control-plane code can use the package through a stable facade
- verification harness is in place
- apps/automation does not depend on package internals as the final architecture
- workflows/applications do not depend on control-plane or package internals

Package Complete does not mean:

- `company_agent` is implemented
- production application workflows are implemented
- worker / queue / outbox exists
- true resume exists
- installed entry-point plugin discovery exists
- entry point discovery exists
- long-running execution semantics are complete
