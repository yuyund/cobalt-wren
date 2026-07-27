'''Read-only execution span query helpers.'''

from __future__ import annotations

from django.db.models import QuerySet

from cobalt_wren.apps.automation.models.execution import ExecutionSpan


def get_span(span_id: int) -> ExecutionSpan | None:
    return ExecutionSpan.objects.select_related('run', 'parent').filter(pk=span_id).first()


def list_spans_for_run(run_id: int) -> QuerySet[ExecutionSpan]:
    return ExecutionSpan.objects.select_related('run', 'parent').filter(run_id=run_id)
