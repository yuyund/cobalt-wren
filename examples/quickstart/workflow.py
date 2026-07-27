"""Executable version of the README Native workflow quickstart."""

from __future__ import annotations

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
