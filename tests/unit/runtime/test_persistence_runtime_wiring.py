"""Runtime wiring regressions for persistence backends."""

from __future__ import annotations

import pytest

from langgraph_automation.apps.automation.models.run import Run
from langgraph_automation.apps.automation.models.workflow import Workflow
from langgraph_automation.apps.automation.services.runtime import build_graph_runtime
from langgraph_automation.integrations.artifact.memory_store import MemoryArtifactStore
from langgraph_automation.integrations.checkpoint.memory_store import MemoryCheckpointStore
from tests.support.persistence import DurabilityLevel, artifact_backend_specs, checkpoint_backend_specs


@pytest.mark.django_db
def test_runtime_wires_ephemeral_memory_persistence_backends() -> None:
    workflow = Workflow.objects.create(
        name='wf-persistence-runtime',
        definition_payload={'llm': {'enabled': True, 'model': 'test-model'}, 'tools': {'allowed': []}},
    )
    run = Run.objects.create(workflow=workflow, name='run-persistence-runtime')

    runtime = build_graph_runtime(run)

    assert isinstance(runtime.artifact_store, MemoryArtifactStore)
    assert isinstance(runtime.checkpoint_store, MemoryCheckpointStore)
    assert artifact_backend_specs()[0].durability == DurabilityLevel.EPHEMERAL
    assert checkpoint_backend_specs()[0].durability == DurabilityLevel.EPHEMERAL
    assert runtime.artifact_store is not None
    assert runtime.checkpoint_store is not None
