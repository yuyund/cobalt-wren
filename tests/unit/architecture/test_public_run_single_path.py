"""Guards for the public-executable-only Run lifecycle."""
from pathlib import Path
from tests.support.import_scan import collect_import_targets


def test_run_service_has_no_graph_runtime_dependency() -> None:
    modules = collect_import_targets(Path("src/langgraph_automation/apps/automation/services/runs.py"))
    assert not any(module.startswith("langgraph_automation.graphs") for module in modules)


def test_execution_adapter_has_no_graph_runner_dependency() -> None:
    modules = collect_import_targets(Path("src/langgraph_automation/apps/automation/services/execution.py"))
    assert not any(module.startswith("langgraph_automation.graphs") for module in modules)


def test_reference_definition_returns_public_executable() -> None:
    text = Path("src/langgraph_automation/workflows/reference/llm_echo_summary/definition.py").read_text()
    assert "LlmEchoSummaryExecutable" in text
    assert "GraphDefinition" not in text
