"""Minimal sequential Native workflow example.

This module is an example source file. Importing the package does not register
it with the engine.
"""

from __future__ import annotations

from collections.abc import Mapping

from cobalt_wren.native import NativeWorkflowContext, workflow


def normalize(value: object) -> str:
    return str(value).strip()


def summarize(value: str) -> str:
    return f"Summary: {value}"


@workflow(name="Document summary", tags=("example",))
async def document_summary(
    ctx: NativeWorkflowContext,
    request: Mapping[str, object],
) -> Mapping[str, object]:
    normalized: str = await ctx.step(
        "normalize", normalize, request.get("text", "")
    )
    summary: str = await ctx.step("summarize", summarize, normalized)
    return {"summary": summary}


PLUGIN = document_summary.plugin(
    plugin_name="examples.native.sequential",
    workflow_kind="examples.native.document-summary",
)
