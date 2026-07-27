"""Progressive-disclosure recipes built on the Native step API."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from cobalt_wren.native.definitions import NativeStepDefinition


def sequential_workflow(
    *,
    name: str,
    steps: Sequence[NativeStepDefinition[object]],
    description: str = "",
    version: str = "0.1.0",
):
    """Build a workflow that passes each step result to the next step."""

    if not steps:
        raise ValueError("sequential_workflow requires at least one step")

    from cobalt_wren.native import NativeWorkflowContext, workflow

    @workflow(
        name=name,
        description=description,
        version=version,
        tags=("recipe", "sequential"),
    )
    async def generated(
        ctx: NativeWorkflowContext,
        request: Mapping[str, object],
    ) -> object:
        value: object = dict(request)
        for definition in steps:
            value = await ctx.step(
                definition.name,
                definition.function,
                value,
                retry=definition.retry,
                timeout_seconds=definition.timeout_seconds,
            )
        return value

    return generated


__all__ = ["sequential_workflow"]
