from pathlib import Path

import pytest

from langgraph_automation.scaffold import WorkflowScaffoldOptions, create_workflow_scaffold


def test_plain_python_scaffold_is_deterministic(tmp_path: Path) -> None:
    target = create_workflow_scaffold(WorkflowScaffoldOptions(distribution_name="invoice-approval", workflow_kind="finance.invoice_approval", checkpoint_store=True, resumable=True, output_directory=tmp_path))
    assert (target / "pyproject.toml").exists()
    assert 'invoice_approval = "invoice_approval:create_plugin"' not in (target / "pyproject.toml").read_text()
    assert 'invoice-approval = "invoice_approval:create_plugin"' in (target / "pyproject.toml").read_text()
    workflow = (target / "src" / "invoice_approval" / "workflow.py").read_text()
    assert "def resume" in workflow
    assert "from langgraph." not in workflow.lower()


def test_resumable_scaffold_requires_checkpoint_store(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="checkpoint-store"):
        create_workflow_scaffold(WorkflowScaffoldOptions(distribution_name="bad-workflow", workflow_kind="bad.workflow", resumable=True, output_directory=tmp_path))
