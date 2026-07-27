# Cobalt Wren

Cobalt Wren is a Python-first workflow toolkit for explicit, observable
execution. Write workflows as ordinary async Python, declare runtime
requirements, validate them locally, and operate them through a Django control
plane. LangGraph and LlamaIndex Workflows are optional integrations rather than
foundation requirements.

> **Status:** 0.1.0 release candidate. The public API is intentionally narrow,
> but breaking changes may still occur before 1.0.

## Install

Cobalt Wren requires Python 3.12 or newer.

```bash
pip install cobalt-wren
```

PostgreSQL support is optional:

```bash
pip install "cobalt-wren[postgres]"
```

Install workflow frameworks and LLM provider SDKs directly in the consuming
application. Cobalt Wren supplies adapter contracts and helpers but does not own
their installation or version policy. For example:

```bash
pip install cobalt-wren langgraph
pip install cobalt-wren llama-index-workflows
pip install cobalt-wren litellm
```

## Write a Native workflow

```python
from collections.abc import Mapping

from cobalt_wren.native import NativeWorkflowContext, workflow


@workflow("example.greeting")
async def greeting(
    ctx: NativeWorkflowContext,
    request: Mapping[str, object],
) -> dict[str, object]:
    name = str(request.get("name", "world"))

    def build_message(value: str) -> str:
        return f"Hello, {value}."

    message = await ctx.step("build-message", build_message, name)

    await ctx.progress.update(current=1, total=1, message="Complete")
    ctx.metric.record("messages.processed", 1, unit="message")
    return {"message": message}
```

The executable source is maintained at `examples/quickstart/workflow.py`.
Save it as `workflow.py`, then inspect, validate, and run it locally:

```bash
cobalt-wren native-inspect workflow:greeting
cobalt-wren native-validate workflow:greeting
cobalt-wren native-run workflow:greeting --input '{"name":"Cobalt"}'
```

Generate a distributable workflow package:

```bash
cobalt-wren init-workflow \
  --name example-workflow \
  --kind example.workflow \
  --framework native \
  --output .
```

## What the control plane provides

- explicit workflow references and fail-closed resolution
- canonical run, span, event, artifact, checkpoint, and action records
- bounded and redacted persistence
- audit, permissions, diagnostics, and lifecycle operations
- framework-neutral LLM and tool observation boundaries
- versioned integration-native projections with generic fallback rendering
- optional Django UI for runs, diagnostics, integrations, and live telemetry

Cobalt Wren does not force every workflow framework into a universal state
model. It stabilizes common facts, meanings, and operations while retaining
framework-specific detail in versioned projections.

## Framework integrations

External workflow objects remain opaque to the foundation. Integration providers
use public execution capabilities and emit stable lifecycle observations plus
versioned integration detail. Importing the foundation does not import
LangGraph or LlamaIndex Workflows.

Core design rules are documented in `docs/architecture/design/DESIGN_PRINCIPLES.md` and `docs/architecture/design/DEVELOPMENT_COMPATIBILITY_POLICY.md`.

The observation model is documented in:

- `docs/architecture/decisions/0001-observation-layers.md`
- `docs/architecture/decisions/0002-schema-id-policy.md`
- `docs/architecture/OBSERVATION_ARCHITECTURE_ROADMAP.md`

## Runtime configuration

Deployment configuration selects providers, tools, stores, event sinks, and
safety policy. Workflow input cannot grant capabilities or supply credentials.
Secrets are resolved during runtime assembly and are not exposed to workflow
build contexts.

Memory artifact and checkpoint stores are ephemeral defaults. Filesystem stores
are explicit process-durable options. Store durability does not by itself imply
execution resume.

## Extension API

External distributions should import public contracts from `cobalt_wren.api`
and supported authoring or integration facades. Plugins may be registered
explicitly or discovered through the `cobalt_wren.plugins` entry-point group.

Start with:

- `docs/workflows/authoring/WORKFLOW_AUTHOR_GUIDE.md`
- `docs/api/surface/API_SURFACE.md`
- `docs/contracts/core/CONTRACTS.md`
- `docs/release/PYPI_RELEASE_CHECKLIST.md`

## License

Copyright 2026 Yudai Maruyama.

Licensed under the Apache License, Version 2.0. See `LICENSE` and `NOTICE`.
