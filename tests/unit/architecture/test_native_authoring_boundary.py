"""Architecture guards for the provisional Native Authoring surface."""

from __future__ import annotations

import ast
from collections.abc import Mapping
from pathlib import Path

from cobalt_wren.api.plugins import Plugin
from cobalt_wren.api.workflow import WorkflowContribution
from cobalt_wren.native import NativeWorkflowContext, workflow


NATIVE_MODULE = Path("src/cobalt_wren/native/__init__.py")


def test_native_public_module_does_not_import_django_or_workflow_oss() -> None:
    tree = ast.parse(NATIVE_MODULE.read_text(encoding="utf-8"))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imports.append(node.module)

    assert not any(module == "django" or module.startswith("django.") for module in imports)
    assert not any(
        module == "langgraph" or module.startswith("langgraph.")
        for module in imports
    )
    assert not any(module == "workflows" or module.startswith("workflows.") for module in imports)


def test_native_conversion_produces_ordinary_public_contract_objects() -> None:
    @workflow(name="Boundary workflow")
    async def boundary_workflow(
        ctx: NativeWorkflowContext,
        request: Mapping[str, object],
    ) -> Mapping[str, object]:
        del ctx
        return request

    contribution = boundary_workflow.contribution(kind="test.native.boundary")
    plugin = boundary_workflow.plugin(
        plugin_name="test-native-boundary",
        workflow_kind="test.native.boundary",
    )

    assert isinstance(contribution, WorkflowContribution)
    assert isinstance(plugin, Plugin)
    assert len(plugin.contributions.workflows) == 1
    plugin_contribution = plugin.contributions.workflows[0]
    assert isinstance(plugin_contribution, WorkflowContribution)
    assert plugin_contribution.kind == contribution.kind
    assert plugin_contribution.definition.metadata == contribution.definition.metadata
    assert plugin_contribution.definition.requirements == contribution.definition.requirements
    assert plugin_contribution.definition.extra == contribution.definition.extra
    assert contribution.definition.extra["integration_id"] == "native"
    assert contribution.definition.extra["lifecycle_events_owner"] == "control_plane"

def test_foundation_execution_path_has_no_native_specific_import_or_branch() -> None:
    foundation_paths = (
        Path("src/cobalt_wren/workflows/adapter.py"),
        Path("src/cobalt_wren/workflows/prepare.py"),
        Path("src/cobalt_wren/api/engine.py"),
        Path("src/cobalt_wren/apps/automation/services/execution.py"),
        Path("src/cobalt_wren/apps/automation/services/runs.py"),
    )

    for path in foundation_paths:
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text)
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imports.append(node.module)
        assert not any(
            module == "cobalt_wren.native"
            or module.startswith("cobalt_wren.native.")
            or module == "cobalt_wren.integrations.native"
            or module.startswith("cobalt_wren.integrations.workflows.native_provider")
            for module in imports
        ), path
        assert 'integration_id == "native"' not in text
        assert "integration_id == 'native'" not in text
