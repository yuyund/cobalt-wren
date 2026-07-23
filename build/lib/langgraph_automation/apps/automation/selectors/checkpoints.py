'''Read-only checkpoint metadata query helpers.'''

from __future__ import annotations

from django.db.models import QuerySet

from langgraph_automation.apps.automation.models.checkpoint import CheckpointMetadata


def get_checkpoint_metadata(checkpoint_metadata_id: int) -> CheckpointMetadata | None:
    return CheckpointMetadata.objects.select_related('run', 'span').filter(pk=checkpoint_metadata_id).first()


def list_checkpoints_for_run(run_id: int) -> QuerySet[CheckpointMetadata]:
    return CheckpointMetadata.objects.select_related('run', 'span').filter(run_id=run_id)
