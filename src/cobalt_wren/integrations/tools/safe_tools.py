"""Safe toy tools used for runtime wiring tests."""

from __future__ import annotations

import json
from typing import Any

from cobalt_wren.core.redaction import redact_text
from cobalt_wren.core.summary import preview_text, summarize_value, truncate_text
from cobalt_wren.integrations.tools.base import ToolResult

ECHO_TOOL_NAME = "echo"


def _safe_preview(value: Any) -> str:
    if isinstance(value, str):
        return truncate_text(preview_text(value), max_chars=300)
    summarized = summarize_value(value)
    return truncate_text(preview_text(json.dumps(summarized, ensure_ascii=False, sort_keys=True, default=str)), max_chars=300)


class EchoTool:
    """Echo back a redacted bounded preview without touching external systems."""

    def __call__(self, **kwargs: Any) -> ToolResult:
        text = kwargs.get('text', '')
        preview = _safe_preview(text)
        safe_output = redact_text(preview)
        return ToolResult(
            output=safe_output,
            output_summary=safe_output,
            exit_code=0,
            metadata={
                'tool_name': ECHO_TOOL_NAME,
                'input_type': type(text).__name__,
                'arg_keys': sorted(kwargs.keys()),
            },
        )
