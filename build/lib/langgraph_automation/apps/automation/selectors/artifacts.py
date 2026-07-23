'''Read-only artifact query helpers.'''

from __future__ import annotations

from django.db.models import QuerySet

from langgraph_automation.apps.automation.models.artifact import Artifact


def get_artifact(artifact_id: int) -> Artifact | None:
    return Artifact.objects.select_related('run', 'span').filter(pk=artifact_id).first()


def list_artifacts_for_run(run_id: int) -> QuerySet[Artifact]:
    return Artifact.objects.select_related('run', 'span').filter(run_id=run_id)
