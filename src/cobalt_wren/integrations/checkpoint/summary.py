"""Bounded, redacted checkpoint state summaries."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from cobalt_wren.core.summary import summarize_mapping as core_summarize_mapping


def summarize_state(state: Mapping[str, Any] | Any) -> dict[str, Any]:
    """Return a bounded summary of checkpoint state."""

    if isinstance(state, Mapping):
        return core_summarize_mapping(state)
    return {
        'keys': ['value'],
        'types': {'value': type(state).__name__},
        'sizes': {},
        'preview': {'value': state},
    }


def format_state_summary(state: Mapping[str, Any] | Any) -> str:
    """Return the checkpoint state summary as JSON."""

    return json.dumps(summarize_state(state), ensure_ascii=False, sort_keys=True, default=str)
