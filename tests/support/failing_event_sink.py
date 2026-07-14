"""Failing EventSink test doubles."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from tests.support.recording_event_sink import RecordingEventSink


class FailingSpanFailedEventSink(RecordingEventSink):
    """Recording sink that fails when span_failed is called."""

    def __init__(self, exc: Exception | None = None) -> None:
        super().__init__()
        self.exc = exc or RuntimeError('sink failure')

    def span_failed(self, span, error_message: str, metrics: Mapping[str, Any] | None = None, metadata: Mapping[str, Any] | None = None):  # type: ignore[override]
        raise self.exc


class FailingRunFailedEventSink(RecordingEventSink):
    """Recording sink that fails when run_failed is called."""

    def __init__(self, exc: Exception | None = None) -> None:
        super().__init__()
        self.exc = exc or RuntimeError('sink failure')

    def run_failed(self, run_id: int, error_message: str, payload: Mapping[str, Any] | None = None):  # type: ignore[override]
        raise self.exc


class FailingGraphEventSink(RecordingEventSink):
    """Recording sink that fails when graph failure events are emitted."""

    def __init__(self, exc: Exception | None = None) -> None:
        super().__init__()
        self.exc = exc or RuntimeError('sink failure')

    def span_failed(self, span, error_message: str, metrics: Mapping[str, Any] | None = None, metadata: Mapping[str, Any] | None = None):  # type: ignore[override]
        raise self.exc

    def run_failed(self, run_id: int, error_message: str, payload: Mapping[str, Any] | None = None):  # type: ignore[override]
        raise self.exc
