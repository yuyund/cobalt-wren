from pathlib import Path
from tests.support.import_scan import collect_import_targets

def test_run_live_projection_does_not_depend_on_workflow_frameworks_or_packages() -> None:
    path = Path("src/cobalt_wren/apps/automation/ui/run_live.py")
    modules = collect_import_targets(path)
    assert not any(module == "langgraph" or module.startswith("langgraph.") for module in modules)
    assert not any("workflows" in module for module in modules)
    assert not any(module.startswith("plain_python_workflow") for module in modules)
    assert "WorkflowDefinition" not in path.read_text()
    assert "WorkflowContribution" not in path.read_text()

def test_run_live_projection_contains_no_renderer_framework_details() -> None:
    source = Path("src/cobalt_wren/apps/automation/ui/run_live.py").read_text()
    assert "tabler" not in source.lower()
    assert "bootstrap" not in source.lower()
    assert "template_name" not in source
    assert "bg-green" not in source
    assert "dynamic/components" not in source

def test_run_component_registry_is_owned_by_web_renderer() -> None:
    source = Path("src/cobalt_wren/apps/web/presentation/run_components.py").read_text()
    assert "dynamic/components/" in source
    assert "WorkflowDefinition" not in source
    assert "WorkflowContribution" not in source
