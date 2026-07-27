'''Read-only run event query helpers.'''

from __future__ import annotations

from django.db.models import QuerySet

from cobalt_wren.apps.automation.models.event import RunEvent


def get_event(event_id: int) -> RunEvent | None:
    return RunEvent.objects.select_related('run', 'span').filter(pk=event_id).first()


def list_events_for_run(run_id: int) -> QuerySet[RunEvent]:
    return RunEvent.objects.select_related('run', 'span').filter(run_id=run_id)
