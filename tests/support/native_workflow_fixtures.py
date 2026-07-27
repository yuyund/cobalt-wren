"""Explicit Native workflow fixtures for engine and service tests."""

from __future__ import annotations

from collections.abc import Mapping

from cobalt_wren.api.plugins import Plugin
from cobalt_wren.api.workflow import WorkflowRequirements
from cobalt_wren.native import NativeWorkflowContext, workflow

TEST_NATIVE_WORKFLOW_KIND = "test.native.workflow"
TEST_REQUIRED_WORKFLOW_KIND = "test.native.required"


@workflow(name="Test Native workflow")
async def TEST_NATIVE_WORKFLOW(
    ctx: NativeWorkflowContext,
    request: Mapping[str, object],
) -> Mapping[str, object]:
    value = await ctx.step("echo", lambda item: item, request.get("value"))
    return {"value": value}


@workflow(name="Required capabilities workflow")
async def TEST_REQUIRED_WORKFLOW(
    ctx: NativeWorkflowContext,
    request: Mapping[str, object],
) -> Mapping[str, object]:
    del request
    ctx.require_provider("default")
    ctx.require_tool("echo")
    return {"ready": True}


def create_test_native_plugin() -> Plugin:
    return TEST_NATIVE_WORKFLOW.plugin(
        plugin_name="tests.native.workflow",
        workflow_kind=TEST_NATIVE_WORKFLOW_KIND,
    )


def create_required_native_plugin() -> Plugin:
    return TEST_REQUIRED_WORKFLOW.plugin(
        plugin_name="tests.native.required",
        workflow_kind=TEST_REQUIRED_WORKFLOW_KIND,
        requirements=WorkflowRequirements(
            provider_profiles=("default",),
            tools=("echo",),
        ),
    )
