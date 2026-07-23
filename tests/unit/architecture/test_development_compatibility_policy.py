"""Guards against reintroducing development-only compatibility shims."""
from pathlib import Path


def test_removed_public_aliases_do_not_return() -> None:
    engine = Path("src/langgraph_automation/api/engine.py").read_text()
    prepared = Path("src/langgraph_automation/workflows/prepare.py").read_text()
    result = Path(
        "src/langgraph_automation/apps/automation/services/execution_result.py"
    ).read_text()
    assert "def graph(" not in engine
    assert "def graph(" not in prepared
    assert "def last_node_name(" not in result


def test_run_api_has_no_explicit_prepared_workflow_injection() -> None:
    text = Path("src/langgraph_automation/apps/automation/services/runs.py").read_text()
    start_signature = text[text.index("def start_run("):text.index(") -> RunActionResult:", text.index("def start_run("))]
    retry_signature = text[text.index("def retry_run("):text.index(") -> RunActionResult:", text.index("def retry_run("))]
    assert "prepared_workflow:" not in start_signature
    assert "event_sink:" not in start_signature
    assert "prepared_workflow:" not in retry_signature
    assert "event_sink:" not in retry_signature


def test_policy_distinguishes_compatibility_from_correctness() -> None:
    text = Path(
        "docs/architecture/design/DEVELOPMENT_COMPATIBILITY_POLICY.md"
    ).read_text()
    assert "Backward compatibility is therefore not a design requirement" in text
    assert "correctness properties rather than consumer compatibility" in text
