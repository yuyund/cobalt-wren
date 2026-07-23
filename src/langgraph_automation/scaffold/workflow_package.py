"""Deterministic external workflow package scaffolding."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")
_KIND_RE = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$")


@dataclass(frozen=True, slots=True)
class WorkflowScaffoldOptions:
    distribution_name: str
    workflow_kind: str
    framework: str = "plain-python"
    resumable: bool = False
    artifact_store: bool = False
    checkpoint_store: bool = False
    output_directory: Path = Path(".")
    force: bool = False


def _module_name(distribution_name: str) -> str:
    return distribution_name.replace("-", "_")


def _class_name(distribution_name: str) -> str:
    return "".join(part.capitalize() for part in re.split(r"[-_]", distribution_name)) + "Workflow"


def _validate(options: WorkflowScaffoldOptions) -> None:
    if not _NAME_RE.fullmatch(options.distribution_name):
        raise ValueError("distribution name must begin with a letter and contain only letters, digits, '-' or '_'")
    if not _KIND_RE.fullmatch(options.workflow_kind):
        raise ValueError("workflow kind must be a lowercase dotted identifier")
    if options.framework not in {"plain-python", "langgraph"}:
        raise ValueError("framework must be plain-python or langgraph")
    if options.resumable and not options.checkpoint_store:
        raise ValueError("resumable scaffolds require --checkpoint-store")


def create_workflow_scaffold(options: WorkflowScaffoldOptions) -> Path:
    _validate(options)
    module = _module_name(options.distribution_name)
    target = options.output_directory.resolve() / options.distribution_name
    if target.exists() and any(target.iterdir()) and not options.force:
        raise FileExistsError(f"target directory is not empty: {target}")
    target.mkdir(parents=True, exist_ok=True)
    package = target / "src" / module
    tests = target / "tests"
    package.mkdir(parents=True, exist_ok=True)
    tests.mkdir(parents=True, exist_ok=True)
    files = _render_files(options, module)
    for relative, content in files.items():
        path = target / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return target


def _render_files(options: WorkflowScaffoldOptions, module: str) -> dict[str, str]:
    class_name = _class_name(options.distribution_name)
    dependencies = ['"langgraph-automation>=0.1.0"']
    if options.framework == "langgraph":
        dependencies.append('"langgraph>=0.2"')
    requirements = []
    if options.artifact_store:
        requirements.append("artifact_store=True")
    if options.checkpoint_store:
        requirements.append("checkpoint_store=True")
    requirements_text = ", ".join(requirements)
    workflow_source = _plain_workflow(options, class_name) if options.framework == "plain-python" else _langgraph_workflow(options, class_name)
    return {
        "pyproject.toml": f'''[build-system]\nrequires = ["setuptools>=68"]\nbuild-backend = "setuptools.build_meta"\n\n[project]\nname = "{options.distribution_name}"\nversion = "0.1.0"\nrequires-python = ">=3.12"\ndependencies = [{", ".join(dependencies)}]\n\n[project.entry-points."langgraph_automation.plugins"]\n{module.replace("_", "-")} = "{module}:create_plugin"\n\n[tool.setuptools]\npackage-dir = {{"" = "src"}}\n\n[tool.setuptools.packages.find]\nwhere = ["src"]\n''',
        "README.md": f'''# {options.distribution_name}\n\nGenerated external workflow package for `{options.workflow_kind}` using `{options.framework}`.\n\n```bash\npython -m pytest\npython -m pip wheel .\n```\n''',
        f"src/{module}/__init__.py": '''from .plugin import WORKFLOW_KIND, create_plugin\n\n__all__ = ["WORKFLOW_KIND", "create_plugin"]\n''',
        f"src/{module}/plugin.py": f'''from __future__ import annotations\n\nfrom langgraph_automation.api.plugins import PLUGIN_API_VERSION, Plugin, PluginContributions, PluginMetadata\nfrom langgraph_automation.api.workflow import WorkflowContribution, WorkflowDefinition, WorkflowMetadata, WorkflowRequirements\n\nfrom .workflow import build_workflow\n\nWORKFLOW_KIND = "{options.workflow_kind}"\n\n\ndef create_plugin() -> Plugin:\n    contribution = WorkflowContribution(\n        kind=WORKFLOW_KIND,\n        definition=WorkflowDefinition(\n            kind=WORKFLOW_KIND,\n            metadata=WorkflowMetadata(name="{class_name}", version="0.1.0", metadata={{"framework": "{options.framework}"}}),\n            requirements=WorkflowRequirements({requirements_text}),\n            build=build_workflow,\n            input_schema={{"type": "object", "properties": {{"message": {{"type": "string"}}}}, "required": ["message"]}},\n            output_schema={{"type": "object", "properties": {{"message": {{"type": "string"}}}}}},\n            extra={{"capabilities": {['execute', 'resume'] if options.resumable else ['execute']!r}}},\n        ),\n    )\n    return Plugin(\n        metadata=PluginMetadata(name="{options.distribution_name}", version="0.1.0", plugin_types=("workflow",), provides={{"workflows": (WORKFLOW_KIND,)}}, metadata={{"plugin_api_version": PLUGIN_API_VERSION}}),\n        contributions=PluginContributions(workflows=(contribution,)),\n    )\n''',
        f"src/{module}/workflow.py": workflow_source,
        "tests/test_contract.py": f'''from {module} import WORKFLOW_KIND, create_plugin\nfrom langgraph_automation.testing import WorkflowContractSuite\n\n\ndef test_workflow_contract() -> None:\n    suite = WorkflowContractSuite(plugin_factory=create_plugin, workflow_kind=WORKFLOW_KIND)\n    suite.assert_declared()\n    suite.assert_framework_neutral_definition()\n    suite.assert_buildable()\n    suite.assert_executes(input_payload={{"message": "hello"}})\n''',
        "tests/test_distribution.py": f'''from importlib import metadata\n\n\ndef test_entry_point_is_declared() -> None:\n    entry = next(item for item in metadata.entry_points().select(group="langgraph_automation.plugins") if item.name == "{module.replace('_', '-')}")\n    plugin = entry.load()()\n    assert plugin.metadata.name == "{options.distribution_name}"\n''',
        ".gitignore": "/build/\n/dist/\n*.egg-info/\n__pycache__/\n.pytest_cache/\n",
    }


def _plain_workflow(options: WorkflowScaffoldOptions, class_name: str) -> str:
    resume_import = ", WorkflowResumeRequest" if options.resumable else ""
    resume_method = '''\n    def resume(self, request: WorkflowResumeRequest, *, context: WorkflowExecutionContext) -> WorkflowExecutionResult:\n        return WorkflowExecutionResult(output={"message": str(request.value.get("message", "resumed"))})\n''' if options.resumable else ""
    status = 'status="paused", output={"message": message, "checkpoint_id": "replace-with-durable-checkpoint"}' if options.resumable else 'output={"message": message}'
    return f'''from __future__ import annotations\n\nfrom collections.abc import Mapping\nfrom dataclasses import dataclass\n\nfrom langgraph_automation.api.workflow import WorkflowBuildContext, WorkflowExecutionContext, WorkflowExecutionResult{resume_import}\n\n\n@dataclass(frozen=True, slots=True)\nclass {class_name}:\n    def execute(self, input_payload: Mapping[str, object], *, context: WorkflowExecutionContext) -> WorkflowExecutionResult:\n        message = str(input_payload.get("message", ""))\n        if not message:\n            raise ValueError("message is required")\n        return WorkflowExecutionResult({status})\n{resume_method}\n\ndef build_workflow(context: WorkflowBuildContext) -> {class_name}:\n    return {class_name}()\n'''


def _langgraph_workflow(options: WorkflowScaffoldOptions, class_name: str) -> str:
    return '''from __future__ import annotations\n\nfrom typing import TypedDict\nfrom langgraph.graph import END, START, StateGraph\nfrom langgraph_automation.api.workflow import WorkflowBuildContext\n\n\nclass State(TypedDict):\n    message: str\n\n\ndef _process(state: State) -> State:\n    return {{"message": state["message"]}}\n\n\ndef build_workflow(context: WorkflowBuildContext):\n    graph = StateGraph(State)\n    graph.add_node("process", _process)\n    graph.add_edge(START, "process")\n    graph.add_edge("process", END)\n    return graph.compile()\n'''
