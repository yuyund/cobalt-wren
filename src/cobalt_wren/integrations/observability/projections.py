"""Optional sink protocol for versioned integration-specific projections."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, runtime_checkable

from cobalt_wren.integrations.observability.types import SpanRef


@runtime_checkable
class IntegrationProjectionSink(Protocol):
    def integration_projection(
        self,
        run_id: int,
        *,
        integration_id: str,
        schema_id: str,
        owner_kind: str,
        payload: Mapping[str, object],
        span: SpanRef | None = None,
        owner_external_id: str = "",
        title: str = "",
        retention_class: str = "execution_detail",
        classification: str = "internal",
        projection_kind: str = "event",
        subject_kind: str = "run",
        subject_external_id: str = "",
        sequence: int = 0,
        occurred_at: object | None = None,
    ) -> object: ...
