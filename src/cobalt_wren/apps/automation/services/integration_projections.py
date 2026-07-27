"""Safe persistence and selection for integration-specific projections."""

from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from cobalt_wren.apps.automation.models.execution import ExecutionSpan
from cobalt_wren.apps.automation.models.integration_projection import (
    IntegrationProjectionKind,
    IntegrationProjectionOwnerKind,
    IntegrationProjectionRecord,
    IntegrationProjectionSubjectKind,
)
from cobalt_wren.apps.automation.models.run import Run
from cobalt_wren.apps.automation.services.diagnostics import (
    build_bounded_diagnostic,
)


_ALLOWED_CLASSIFICATIONS = {"public", "internal", "confidential", "restricted"}
_ALLOWED_RETENTION_CLASSES = {"transient", "diagnostic", "execution_detail", "audit"}


def projection_retention_days(retention_class: str) -> int:
    defaults = {
        "transient": 1,
        "diagnostic": 7,
        "execution_detail": 30,
        "audit": 365,
    }
    configured = getattr(settings, "COBALT_WREN_PROJECTION_RETENTION_DAYS", {})
    if isinstance(configured, dict):
        value = configured.get(retention_class, defaults.get(retention_class, 30))
    else:
        value = defaults.get(retention_class, 30)
    return max(1, int(value))


def record_integration_projection(
    *,
    run: Run,
    integration_id: str,
    schema_id: str,
    owner_kind: str,
    payload: object,
    span: ExecutionSpan | None = None,
    owner_external_id: str = "",
    title: str = "",
    retention_class: str = "execution_detail",
    classification: str = "internal",
    projection_kind: str = "event",
    subject_kind: str = "run",
    subject_external_id: str = "",
    sequence: int = 0,
    occurred_at=None,
) -> IntegrationProjectionRecord:
    if owner_kind not in IntegrationProjectionOwnerKind.values:
        raise ValueError("unsupported integration projection owner kind")
    if projection_kind not in IntegrationProjectionKind.values:
        raise ValueError("unsupported integration projection kind")
    if subject_kind not in IntegrationProjectionSubjectKind.values:
        raise ValueError("unsupported integration projection subject kind")
    if retention_class not in _ALLOWED_RETENTION_CLASSES:
        raise ValueError("unsupported integration projection retention class")
    if classification not in _ALLOWED_CLASSIFICATIONS:
        raise ValueError("unsupported integration projection classification")
    if span is not None and span.run_id != run.pk:
        raise ValueError("integration projection span must belong to the run")
    bounded = build_bounded_diagnostic(payload)
    return IntegrationProjectionRecord.objects.create(
        run=run,
        span=span,
        integration_id=integration_id.strip()[:100],
        schema_id=schema_id.strip()[:200],
        owner_kind=owner_kind,
        owner_external_id=owner_external_id.strip()[:255],
        title=title.strip()[:200],
        projection_kind=projection_kind,
        subject_kind=subject_kind,
        subject_external_id=subject_external_id.strip()[:255],
        sequence=max(0, int(sequence)),
        occurred_at=occurred_at or timezone.now(),
        payload=bounded.payload,
        byte_size=bounded.byte_size,
        truncated=bounded.truncated,
        truncation_reason=bounded.truncation_reason,
        retention_class=retention_class,
        classification=classification,
        expires_at=timezone.now() + timedelta(days=projection_retention_days(retention_class)),
    )


def active_projections_for_run(run_id: int):
    return IntegrationProjectionRecord.objects.select_related("run", "span").filter(
        run_id=run_id,
        expires_at__gt=timezone.now(),
    )


def active_projections_for_span(span_id: int):
    return IntegrationProjectionRecord.objects.select_related("run", "span").filter(
        span_id=span_id,
        expires_at__gt=timezone.now(),
    )
