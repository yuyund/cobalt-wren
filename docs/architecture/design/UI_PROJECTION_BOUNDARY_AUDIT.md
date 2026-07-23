# UI Projection Boundary Audit

## Finding

The current UI specification dataclasses are framework-neutral, but composition is not. `ui.registry` imports Django models, selectors, policies, and services, while `ui.builders` imports Django `Model` and introspects object attributes. Therefore the current Dynamic UI is a Django control-plane renderer, not a package-level workflow metadata projection boundary.

## Required Boundary

External workflow metadata must remain declarative data owned by `WorkflowMetadata`, schemas, and `WorkflowDefinition.extra`. The package engine must not import Django to expose it. A future projection adapter may translate that public metadata into renderer-specific specs. Renderers must consume projected allowlisted values, never workflow objects, private registries, Django `_meta`, or raw payloads.

## Current Status

- Public workflow metadata and schemas: available without Django.
- External workflow metadata declaration: tested.
- Django UI registry: coupled to control-plane models and services by design today.
- Generic workflow-to-UI projection adapter: not implemented.
- Second renderer: not tested.

This audit intentionally records the boundary before any broad UI refactor.
