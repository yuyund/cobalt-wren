"""Architecture guards for the explicit artifact emission contract."""

from __future__ import annotations

from pathlib import Path

from tests.support.import_scan import collect_import_targets


def test_artifact_emission_module_does_not_import_concrete_stores_or_django() -> None:
    targets = collect_import_targets(Path('src/langgraph_automation/integrations/artifact/emission.py'))

    offenders = [
        target
        for target in targets
        if target.startswith(
            (
                'django',
                'langgraph_automation.apps.automation',
                'langgraph_automation.graphs',
                'langgraph_automation.runtime.assembly',
                'langgraph_automation.integrations.artifact.memory_store',
                'langgraph_automation.integrations.artifact.filesystem_store',
            )
        )
    ]
    assert offenders == []


def test_artifact_emission_module_stays_free_of_store_call_sites() -> None:
    text = Path('src/langgraph_automation/integrations/artifact/emission.py').read_text()

    for token in (
        'ArtifactStore(',
        'MemoryArtifactStore(',
        'FilesystemArtifactStore(',
        'build_artifact_store(',
        'build_checkpoint_store(',
        'transaction.atomic',
    ):
        assert token not in text
