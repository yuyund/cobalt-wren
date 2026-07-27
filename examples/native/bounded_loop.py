"""Bounded loop with explicit occurrence identities."""

from __future__ import annotations

from collections.abc import Mapping

from cobalt_wren.native import NativeWorkflowContext, workflow


@workflow(name="Bounded item processing", tags=("example",))
async def process_items(
    ctx: NativeWorkflowContext,
    request: Mapping[str, object],
) -> Mapping[str, object]:
    outputs: list[str] = []
    items = request.get("items", ())
    if not isinstance(items, (list, tuple)):
        raise TypeError("items must be a list or tuple")
    for index, item in enumerate(items):
        outputs.append(
            await ctx.step(
                "process-item",
                lambda value: str(value).upper(),
                item,
                occurrence_key=str(index),
            )
        )
    return {"items": outputs}
