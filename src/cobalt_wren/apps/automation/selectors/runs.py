'''Read-only run query helpers.'''

from __future__ import annotations

from django.db.models import QuerySet

from cobalt_wren.apps.automation.models.run import Run


def get_run(run_id: int) -> Run | None:
    return Run.objects.select_related('workflow').filter(pk=run_id).first()


def list_runs() -> QuerySet[Run]:
    return Run.objects.select_related('workflow').all()
