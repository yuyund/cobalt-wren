"""Architecture guard for persistence orchestration boundaries."""

from __future__ import annotations

import inspect
from pathlib import Path

from langgraph_automation.apps.automation.services import runs as run_services


def test_execution_path_does_not_call_artifact_or_checkpoint_store_persistence_methods() -> None:
    paths = (
        Path('src/langgraph_automation/apps/automation/services/runtime.py'),
        Path('src/langgraph_automation/apps/automation/services/execution.py'),
        Path('src/langgraph_automation/apps/automation/services/runs.py'),
    )

    forbidden_tokens = (
        'artifact_store.put(',
        'checkpoint_store.save(',
        'ArtifactStore.put(',
        'CheckpointStore.save(',
    )

    for path in paths:
        text = path.read_text().lower()
        offenders = [token for token in forbidden_tokens if token.lower() in text]
        assert offenders == [], f'{path} still references persistence write calls: {offenders}'


def test_application_runtime_does_not_directly_construct_concrete_persistence_stores() -> None:
    path = Path('src/langgraph_automation/apps/automation/services/runtime.py')
    text = path.read_text()

    for token in (
        'MemoryArtifactStore(',
        'FilesystemArtifactStore(',
        'MemoryCheckpointStore(',
        'FilesystemCheckpointStore(',
    ):
        assert token not in text, f'{path} still directly constructs concrete persistence stores: {token}'


def test_application_runtime_does_not_source_physical_store_selection_from_workflow_payload() -> None:
    path = Path('src/langgraph_automation/apps/automation/services/runtime.py')
    text = path.read_text()

    forbidden_tokens = (
        'load_normalized_package_config_from_mapping(run.workflow.definition_payload',
        'normalize_artifact_store_settings(run.workflow.definition_payload',
        'normalize_checkpoint_store_settings(run.workflow.definition_payload',
        'build_package_artifact_store(run.workflow.definition_payload',
        'build_package_checkpoint_store(run.workflow.definition_payload',
        'load_package_config_from_mapping(run.workflow.definition_payload',
    )

    offenders = [token for token in forbidden_tokens if token in text]
    assert offenders == [], f'{path} still sources persistence selection from workflow payload: {offenders}'


def test_run_service_signatures_do_not_accept_physical_persistence_configuration() -> None:
    for func in (run_services.start_run, run_services.retry_run, run_services.cancel_run):
        signature = inspect.signature(func)
        assert 'package_settings' not in signature.parameters, f'{func.__module__}.{func.__name__} still accepts package_settings'
