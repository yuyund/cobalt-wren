"""Centrally managed workflow OSS integration definitions."""

from __future__ import annotations

from cobalt_wren.api.integrations import (
    IntegrationCapability,
    IntegrationDefinition,
    IntegrationMaturity,
    IntegrationSupport,
)

NATIVE_INTEGRATION = IntegrationDefinition(
    integration_id="native",
    distribution="cobalt-wren",
    import_name="cobalt_wren.native",
    provider_path=(
        "cobalt_wren.integrations.workflows.native_provider:"
        "NATIVE_PROVIDER"
    ),
    supported_versions=">=0.1,<1",
    maturity=IntegrationMaturity.PREVIEW,
    detection_priority=110,
    capabilities=(
        IntegrationCapability("execute"),
        IntegrationCapability("step_observability"),
        IntegrationCapability("branching"),
        IntegrationCapability("bounded_iteration"),
        IntegrationCapability("artifacts"),
        IntegrationCapability("progress"),
        IntegrationCapability("metrics"),
        IntegrationCapability("retry"),
        IntegrationCapability(
            "timeout",
            support=IntegrationSupport.PARTIAL,
            limitations=(
                "asynchronous callables are cancelled on timeout",
                "timed-out synchronous callables may continue in their worker thread",
            ),
        ),
        IntegrationCapability(
            "resume",
            support=IntegrationSupport.NONE,
            limitations=("durable resume is not part of the Native MVP",),
        ),
        IntegrationCapability("waiting", support=IntegrationSupport.NONE),
        IntegrationCapability("checkpoints", support=IntegrationSupport.NONE),
        IntegrationCapability(
            "dynamic_views", support=IntegrationSupport.PARTIAL
        ),
    ),
    limitations=(
        "execution is process-local and does not checkpoint arbitrary Python state",
        "cancellation is cooperative at explicit step boundaries and retry delays",
        "synchronous callables cannot be forcibly terminated by a step timeout",
        "durable waiting is not implemented",
    ),
    documentation_ref="docs/workflows/authoring/NATIVE_AUTHORING_USE_CASE_DESIGN.md",
    auto_detection=False,
    metadata={"bundled": True},
)

LANGGRAPH_INTEGRATION = IntegrationDefinition(
    integration_id="langgraph",
    distribution="langgraph",
    import_name="langgraph",
    provider_path=(
        "cobalt_wren.integrations.workflows.langgraph_provider:"
        "LANGGRAPH_PROVIDER"
    ),
    supported_versions=">=1.0,<2",
    maturity=IntegrationMaturity.EXPERIMENTAL,
    detection_priority=100,
    capabilities=(
        IntegrationCapability("execute"),
        IntegrationCapability("node_observability"),
        IntegrationCapability(
            "resume",
            support=IntegrationSupport.PARTIAL,
            limitations=(
                "requires a compiled graph with compatible checkpoint state",
                "checkpoint ownership remains with the workflow or LangGraph backend",
            ),
        ),
        IntegrationCapability(
            "waiting",
            support=IntegrationSupport.PARTIAL,
            limitations=("interrupt payloads are projected as bounded summaries",),
        ),
        IntegrationCapability(
            "checkpoints",
            support=IntegrationSupport.PARTIAL,
            limitations=("the foundation does not copy or interpret LangGraph checkpoints",),
        ),
        IntegrationCapability("dynamic_views", support=IntegrationSupport.PARTIAL),
    ),
    limitations=(
        "subgraph namespaces are retained only when emitted by the public stream API",
        "time travel and checkpoint lineage projection are not implemented",
        "cancellation is cooperative between streamed task events",
    ),
    documentation_ref="docs/architecture/design/OSS_NEUTRAL_WORKFLOW_INTEGRATION.md",
    auto_detection=True,
    metadata={"install_extra": "langgraph"},
)

LLAMAINDEX_WORKFLOWS_INTEGRATION = IntegrationDefinition(
    integration_id="llamaindex-workflows",
    distribution="llama-index-workflows",
    import_name="workflows",
    provider_path=(
        "cobalt_wren.integrations.workflows.llamaindex_provider:"
        "LLAMAINDEX_WORKFLOWS_PROVIDER"
    ),
    supported_versions=">=2.22,<3",
    maturity=IntegrationMaturity.EXPERIMENTAL,
    detection_priority=90,
    capabilities=(
        IntegrationCapability("execute"),
        IntegrationCapability("step_observability"),
        IntegrationCapability(
            "event_observability",
            support=IntegrationSupport.PARTIAL,
            limitations=(
                "only events exposed by WorkflowHandler.stream_events() are projected",
            ),
        ),
        IntegrationCapability(
            "resume",
            support=IntegrationSupport.NONE,
            limitations=("human-input and durable resume routing are not implemented",),
        ),
        IntegrationCapability("waiting", support=IntegrationSupport.NONE),
        IntegrationCapability("checkpoints", support=IntegrationSupport.NONE),
        IntegrationCapability(
            "dynamic_views", support=IntegrationSupport.PARTIAL
        ),
    ),
    limitations=(
        "the synchronous foundation adapter bridges the async workflow handler",
        "cancel and external event injection are not connected to common actions",
        "runtime durability and replay remain owned by the selected Workflows runtime",
    ),
    documentation_ref="docs/architecture/design/OSS_NEUTRAL_WORKFLOW_INTEGRATION.md",
    auto_detection=True,
    metadata={"install_extra": "llamaindex"},
)

SUPPORTED_WORKFLOW_INTEGRATIONS = (
    NATIVE_INTEGRATION,
    LANGGRAPH_INTEGRATION,
    LLAMAINDEX_WORKFLOWS_INTEGRATION,
)

__all__ = [
    "NATIVE_INTEGRATION",
    "LANGGRAPH_INTEGRATION",
    "LLAMAINDEX_WORKFLOWS_INTEGRATION",
    "SUPPORTED_WORKFLOW_INTEGRATIONS",
]
