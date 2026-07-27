"""Helpers for suppressing observability failures without masking primary failures."""

from __future__ import annotations

from collections.abc import Callable, Mapping
import json
import logging
from typing import Any

from cobalt_wren.core.redaction import redact_mapping
from cobalt_wren.core.result_safety import safe_run_error_message
from cobalt_wren.core.summary import summarize_mapping

logger = logging.getLogger(__name__)


def _format_context(context: Mapping[str, Any] | None) -> str:
    if not context:
        return '{}'
    return json.dumps(summarize_mapping(redact_mapping(context)), ensure_ascii=False, sort_keys=True, default=str)


def suppress_observability_failure(operation: Callable[[], None], *, context: Mapping[str, Any] | None = None) -> None:
    """Run an observability operation and suppress any failure it raises."""

    try:
        operation()
    except Exception as exc:  # pragma: no cover - exercised via wrappers/tests
        logger.warning(
            'Observability failure suppressed to preserve primary failure: %s context=%s',
            safe_run_error_message(exc),
            _format_context(context),
        )
