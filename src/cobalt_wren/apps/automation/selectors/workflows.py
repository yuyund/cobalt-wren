'''Read-only workflow query helpers.'''

from __future__ import annotations

from django.db.models import QuerySet

from cobalt_wren.apps.automation.models.workflow import Workflow


def get_workflow(workflow_id: int) -> Workflow | None:
    return Workflow.objects.filter(pk=workflow_id).first()


def list_workflows() -> QuerySet[Workflow]:
    return Workflow.objects.all()
