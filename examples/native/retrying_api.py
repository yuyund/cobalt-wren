"""Explicit retry and timeout policy example."""

from __future__ import annotations

from collections.abc import Mapping

from cobalt_wren.native import NativeWorkflowContext, RetryPolicy, workflow


async def fetch_remote(identifier: str) -> Mapping[str, object]:
    return {"id": identifier, "status": "ready"}


@workflow(name="Retrying API", tags=("example",))
async def retrying_api(
    ctx: NativeWorkflowContext,
    request: Mapping[str, object],
) -> Mapping[str, object]:
    return await ctx.step(
        "fetch-remote",
        fetch_remote,
        str(request.get("id", "")),
        retry=RetryPolicy(max_attempts=3, retry_on=(ConnectionError,)),
        timeout_seconds=10,
    )
