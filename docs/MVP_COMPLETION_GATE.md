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
- built-in reference workflows can serve as examples

## What MVP complete does not mean

MVP complete does not mean:

- production-ready queue / resume / discovery exists
- `company_agent` is implemented
- production application workflows are implemented
- execution path migration is complete
- external plugin discovery exists
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
