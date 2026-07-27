"""Official Native Authoring integration boundary tests."""

from __future__ import annotations

from collections.abc import Mapping

import pytest

from cobalt_wren.api.integrations import IntegrationContext
from cobalt_wren.api.workflow import (
    WorkflowBuildContext,
    WorkflowExecutionContext,
)
from cobalt_wren.integrations.native import integrate_native_workflow
from cobalt_wren.integrations.workflows.definitions import NATIVE_INTEGRATION
from cobalt_wren.integrations.workflows.native_provider import NATIVE_PROVIDER
from cobalt_wren.native import NativeExecutable, NativeWorkflowContext, workflow
from tests.support.recording_event_sink import RecordingEventSink


@workflow(name="Native integration test")
async def _native_workflow(
    ctx: NativeWorkflowContext,
    request: Mapping[str, object],
) -> Mapping[str, object]:
    value = await ctx.step("normalize", lambda item: str(item).strip(), request["value"])
    return {"value": value}


def test_native_definition_is_central_and_provider_owned() -> None:
    assert NATIVE_PROVIDER.definition is NATIVE_INTEGRATION
    assert NATIVE_INTEGRATION.integration_id == "native"
    assert NATIVE_INTEGRATION.distribution == "cobalt-wren"
    assert NATIVE_INTEGRATION.capability("step_observability") is not None
    assert NATIVE_INTEGRATION.capability("resume") is not None
    assert NATIVE_INTEGRATION.capability("resume").support.value == "none"


def test_native_provider_wraps_authoring_object_as_opaque_executable() -> None:
    executable = NATIVE_PROVIDER.wrap(
        _native_workflow,
        context=IntegrationContext(
            workflow_kind="acme.native",
            config={
                "build_context": WorkflowBuildContext(
                    workflow_kind="acme.native"
                )
            },
        ),
    )

    assert isinstance(executable, NativeExecutable)
    sink = RecordingEventSink()
    result = executable.execute(
        {"value": " hello "},
        context=WorkflowExecutionContext(run_id=51, event_sink=sink),
    )

    assert result.output == {"value": "hello"}
    assert result.metadata["integration_id"] == "native"
    assert {item["schema_id"] for item in sink.integration_projections} == {
        "native.step.v1"
    }


def test_integrate_native_workflow_is_thin_convenience_helper() -> None:
    executable = integrate_native_workflow(
        _native_workflow,
        workflow_kind="acme.native.helper",
        build_context=WorkflowBuildContext(
            workflow_kind="acme.native.helper"
        ),
    )

    assert isinstance(executable, NativeExecutable)
    assert executable.execute(
        {"value": " helper "},
        context=WorkflowExecutionContext(),
    ).output == {"value": "helper"}


def test_native_provider_rejects_non_native_target_and_missing_build_context() -> None:
    with pytest.raises(TypeError, match="NativeWorkflow"):
        NATIVE_PROVIDER.wrap(
            object(),
            context=IntegrationContext(workflow_kind="invalid"),
        )

    with pytest.raises(TypeError, match="WorkflowBuildContext"):
        NATIVE_PROVIDER.wrap(
            _native_workflow,
            context=IntegrationContext(workflow_kind="invalid"),
        )
