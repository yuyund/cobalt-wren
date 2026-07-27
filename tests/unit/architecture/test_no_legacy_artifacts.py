"""Architecture guard: legacy artifacts and fake backends must not remain."""

from __future__ import annotations

import re
from pathlib import Path


def test_legacy_notes_and_placeholder_models_are_removed() -> None:
    assert not Path('note.md').exists()
    assert not Path('src/cobalt_wren/apps/automation/models/agent.py').exists()
    assert not Path('src/cobalt_wren/apps/automation/models/config.py').exists()
    assert not Path('src/cobalt_wren/integrations/llm/fake_client.py').exists()
    assert not Path('src/cobalt_wren/integrations/llm/not_configured_client.py').exists()
    assert not Path('src/cobalt_wren/integrations/observability/llm_observer.py').exists()
    assert not Path('src/cobalt_wren/graphs/nodes/executor.py').exists()
    assert not Path('src/cobalt_wren/graphs/llm_echo_summary.py').exists()
    assert not Path('src/cobalt_wren/graphs/nodes/minimal.py').exists()
    assert not Path('src/cobalt_wren/graphs/states.py').exists()
    assert not Path('src/cobalt_wren/graphs/nodes/planner.py').exists()
    assert not Path('src/cobalt_wren/graphs/nodes/summarizer.py').exists()
    assert not Path('src/cobalt_wren/graphs/llm_echo_summary.py').exists()
    assert not Path('src/cobalt_wren/graphs/nodes/minimal.py').exists()
    assert not Path('src/cobalt_wren/graphs/states.py').exists()
    assert not Path('src/cobalt_wren/graphs/nodes/reviewer.py').exists()
    assert not Path('src/cobalt_wren/graphs/routing.py').exists()
    assert not Path('src/cobalt_wren/entrypoints/run_worker.py').exists()
    assert not Path('src/cobalt_wren/integrations/tools/file_tool.py').exists()
    assert not Path('src/cobalt_wren/integrations/tools/shell_tool.py').exists()
    assert not Path('src/cobalt_wren/integrations/artifact/local_store.py').exists()


def test_production_code_has_no_fake_or_placeholder_llm_runners() -> None:
    offenders: list[str] = []
    blocked_terms = (
        'FakeGraphRunner',
        'FakeLLMClient',
        'GRAPH_RUNNER_BACKEND',
        'LLM_BACKEND=fake',
        'NotConfiguredLLMClient',
        'PlaceholderLLMClient',
        'StubLLMClient',
        'DisabledLLMClient',
        'LLMObserver',
    )
    for path in Path('src').rglob('*.py'):
        text = path.read_text()
        if any(term in text for term in blocked_terms):
            offenders.append(str(path))
    assert offenders == []


def test_production_code_has_no_legacy_artifact_store_name() -> None:
    offenders: list[str] = []
    for path in Path('src').rglob('*.py'):
        text = path.read_text()
        if re.search(r'\bLocalArtifactStore\b', text):
            offenders.append(str(path))
    assert offenders == []


def test_tests_support_is_not_imported_from_src() -> None:
    offenders: list[str] = []
    for path in Path('src').rglob('*.py'):
        text = path.read_text()
        if 'tests.support' in text:
            offenders.append(str(path))
    assert offenders == []


def test_observed_tool_registry_does_not_import_django_orm() -> None:
    text = Path('src/cobalt_wren/integrations/tools/observed_registry.py').read_text()
    assert 'django.db' not in text
    assert 'django.models' not in text


def test_graph_nodes_do_not_directly_emit_lifecycle_events() -> None:
    root = Path('src/cobalt_wren/graphs/nodes')
    offenders: list[str] = []
    for path in root.rglob('*.py'):
        text = path.read_text()
        if 'llm_started' in text or 'llm_completed' in text or 'llm_failed' in text or 'tool_started' in text or 'tool_completed' in text or 'tool_failed' in text:
            offenders.append(str(path))
    assert offenders == []


def test_shell_and_file_tool_placeholders_do_not_reappear() -> None:
    for relpath in [
        'src/cobalt_wren/integrations/tools/file_tool.py',
        'src/cobalt_wren/integrations/tools/shell_tool.py',
    ]:
        assert not Path(relpath).exists()


def test_reference_diagnostic_workflow_nodes_are_not_application_placeholders() -> None:
    assert not Path('src/cobalt_wren/graphs/nodes/planner.py').exists()
    assert not Path('src/cobalt_wren/graphs/nodes/summarizer.py').exists()
    assert not Path('src/cobalt_wren/graphs/llm_echo_summary.py').exists()
    assert not Path('src/cobalt_wren/graphs/nodes/minimal.py').exists()
    assert not Path('src/cobalt_wren/graphs/states.py').exists()


def test_graph_package_is_removed() -> None:
    assert not Path("src/cobalt_wren/graphs").exists()
