"""Safe summaries for Run model persistence."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .redaction import REDACTED_VALUE, redact_mapping, redact_text
from .summary import preview_text, truncate_text

_MAX_OUTPUT_PREVIEW_CHARS = 300
_MAX_ERROR_MESSAGE_CHARS = 300
_MAX_SUMMARY_DEPTH = 3
_MAX_SUMMARY_ITEMS = 20


def _type_name(value: Any) -> str:
    if value is None:
        return 'none'
    if isinstance(value, bool):
        return 'bool'
    if isinstance(value, int):
        return 'int'
    if isinstance(value, float):
        return 'float'
    if isinstance(value, str):
        return 'str'
    if isinstance(value, Mapping):
        return 'dict'
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return 'list'
    return type(value).__name__


def _size_of(value: Any) -> int | None:
    if isinstance(value, (Mapping, Sequence)) and not isinstance(value, (str, bytes, bytearray)):
        return len(value)
    if isinstance(value, str):
        return len(value)
    return None


def _bounded_preview(value: Any) -> str:
    return truncate_text(redact_text(str(value)), max_chars=_MAX_OUTPUT_PREVIEW_CHARS)


def _summarize_any(value: Any, *, depth: int) -> Any:
    if depth < 0:
        return REDACTED_VALUE
    if isinstance(value, Mapping):
        return _summarize_mapping(value, depth=depth)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return _summarize_sequence(value, depth=depth)
    if isinstance(value, str):
        return preview_text(value, max_chars=_MAX_OUTPUT_PREVIEW_CHARS)
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return _bounded_preview(value)


def _summarize_sequence(value: Sequence[Any], *, depth: int) -> list[Any]:
    items = list(value)[:_MAX_SUMMARY_ITEMS]
    return [_summarize_any(item, depth=depth - 1) for item in items]


def _summarize_mapping(value: Mapping[str, Any], *, depth: int) -> dict[str, Any]:
    if depth < 0:
        return REDACTED_VALUE
    redacted = redact_mapping(value)
    items = list(redacted.items())[:_MAX_SUMMARY_ITEMS]
    summary: dict[str, Any] = {'keys': [], 'types': {}, 'sizes': {}, 'preview': {}}
    if len(redacted) > _MAX_SUMMARY_ITEMS:
        summary['truncated'] = True
    for key, nested_value in items:
        key_name = str(key)
        summary['keys'].append(key_name)
        summary['types'][key_name] = _type_name(nested_value)
        size = _size_of(nested_value)
        if size is not None:
            summary['sizes'][key_name] = size
        summary['preview'][key_name] = _summarize_any(nested_value, depth=depth - 1)
    return summary


def safe_run_output_payload(value: Any) -> dict[str, Any]:
    """Return a bounded summary safe to persist in Run.output_payload."""

    if isinstance(value, Mapping):
        return {
            'value_type': _type_name(value),
            'size': len(value),
            'summary': _summarize_mapping(value, depth=_MAX_SUMMARY_DEPTH),
        }
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return {
            'value_type': _type_name(value),
            'size': len(value),
            'summary': _summarize_sequence(value, depth=_MAX_SUMMARY_DEPTH),
        }
    if isinstance(value, str):
        return {
            'value_type': 'str',
            'summary': {
                'preview': preview_text(value, max_chars=_MAX_OUTPUT_PREVIEW_CHARS),
                'length': len(value),
            },
        }
    text = str(value)
    return {
        'value_type': _type_name(value),
        'summary': {
            'preview': _bounded_preview(text),
            'length': len(text),
        },
    }


def safe_run_error_message(error: BaseException | str) -> str:
    """Return a redacted, bounded error summary safe to persist in Run.error_message."""

    if isinstance(error, BaseException):
        error_type = type(error).__name__
        raw_message = str(error) or 'operation failed'
    else:
        error_type = 'Error'
        raw_message = error or 'operation failed'
    bounded = truncate_text(redact_text(raw_message), max_chars=_MAX_ERROR_MESSAGE_CHARS).strip()
    if not bounded:
        bounded = REDACTED_VALUE
    return f'{error_type}: {bounded}'
