from __future__ import annotations

from typing import TypedDict

from cobalt_wren.native import NativeWorkflowContext, workflow


class Request(TypedDict):
    name: str


class Result(TypedDict):
    message: str


@workflow("Hello")
async def hello(ctx: NativeWorkflowContext, request: Request) -> Result:
    message = await ctx.step("format-message", lambda value: f"Hello, {value}!", request["name"])
    await ctx.progress.update(current=1, total=1, message="Complete")
    return {"message": message}
