"""Conditional routing with ordinary Python control flow."""

from __future__ import annotations

from collections.abc import Mapping

from cobalt_wren.native import NativeWorkflowContext, workflow


@workflow(name="Conditional review", tags=("example",))
async def conditional_review(
    ctx: NativeWorkflowContext,
    request: Mapping[str, object],
) -> Mapping[str, object]:
    value = str(request.get("value", ""))
    if bool(request.get("uppercase")):
        result = await ctx.step("uppercase", str.upper, value)
    else:
        result = await ctx.step("lowercase", str.lower, value)
    return {"result": result}
