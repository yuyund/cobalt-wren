from pathlib import Path

import pytest

from cobalt_wren.scaffold import WorkflowScaffoldOptions, create_workflow_scaffold


def test_plain_python_scaffold_is_deterministic(tmp_path: Path) -> None:
    target = create_workflow_scaffold(WorkflowScaffoldOptions(distribution_name="invoice-approval", workflow_kind="finance.invoice_approval", checkpoint_store=True, resumable=True, output_directory=tmp_path))
    assert (target / "pyproject.toml").exists()
    assert 'invoice_approval = "invoice_approval:create_plugin"' not in (target / "pyproject.toml").read_text()
    assert 'invoice-approval = "invoice_approval:create_plugin"' in (target / "pyproject.toml").read_text()
    workflow = (target / "src" / "invoice_approval" / "workflow.py").read_text()
    assert "def resume" in workflow
    assert "example-non-durable-checkpoint" in workflow
    assert "from langgraph." not in workflow.lower()
    assert "does not implement durable checkpoint recovery" in (target / "README.md").read_text()


def test_resumable_scaffold_requires_checkpoint_store(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="checkpoint-store"):
        create_workflow_scaffold(WorkflowScaffoldOptions(distribution_name="bad-workflow", workflow_kind="bad.workflow", resumable=True, output_directory=tmp_path))


def test_langgraph_scaffold_uses_official_integration_helper(tmp_path: Path) -> None:
    target = create_workflow_scaffold(
        WorkflowScaffoldOptions(
            distribution_name="graph-review",
            workflow_kind="review.graph",
            framework="langgraph",
            output_directory=tmp_path,
        )
    )

    workflow = (target / "src" / "graph_review" / "workflow.py").read_text()
    pyproject = (target / "pyproject.toml").read_text()

    assert "from cobalt_wren.integrations.langgraph import integrate_langgraph" in workflow
    assert "return integrate_langgraph(" in workflow
    assert '"langgraph>=1.0,<2"' in pyproject
    compile(workflow, str(target / "src" / "graph_review" / "workflow.py"), "exec")


def test_native_scaffold_uses_native_authoring_and_inferred_schema(tmp_path: Path) -> None:
    target = create_workflow_scaffold(
        WorkflowScaffoldOptions(
            distribution_name="native-review",
            workflow_kind="review.native",
            framework="native",
            output_directory=tmp_path,
        )
    )
    workflow = (target / "src" / "native_review" / "workflow.py").read_text()
    assert "@workflow" in workflow
    assert "ctx.step" in workflow
    assert "ctx.progress.update" in workflow
    assert "ctx.metric.record" in workflow
    assert "integrate_native_workflow" in workflow
    compile(workflow, str(target / "src" / "native_review" / "workflow.py"), "exec")


def test_native_scaffold_rejects_resume(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="durable resume"):
        create_workflow_scaffold(
            WorkflowScaffoldOptions(
                distribution_name="native-resume",
                workflow_kind="native.resume",
                framework="native",
                resumable=True,
                checkpoint_store=True,
                output_directory=tmp_path,
            )
        )


def test_native_scaffold_declares_requested_dependencies(tmp_path: Path) -> None:
    target = create_workflow_scaffold(
        WorkflowScaffoldOptions(
            distribution_name="native-dependencies",
            workflow_kind="native.dependencies",
            framework="native",
            provider_profiles=("default",),
            tools=("echo",),
            artifact_store=True,
            event_sinks=("audit",),
            output_directory=tmp_path,
        )
    )
    workflow = (target / "src" / "native_dependencies" / "workflow.py").read_text()
    plugin = (target / "src" / "native_dependencies" / "plugin.py").read_text()
    assert "provider_profiles=('default',)" in workflow
    assert "tools=('echo',)" in workflow
    assert "artifact_store=True" in workflow
    assert "event_sinks=('audit',)" in workflow
    assert "provider_profiles=('default',)" in plugin
    assert "tools=('echo',)" in plugin
