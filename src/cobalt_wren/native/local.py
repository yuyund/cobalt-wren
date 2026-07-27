"""Local Native workflow loading and execution helpers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import ast
import importlib
import inspect
import textwrap

from cobalt_wren.api.engine import create_engine
from cobalt_wren.api.workflow import WorkflowExecutionContext, WorkflowRequirements
from cobalt_wren.native import NativeWorkflow
from cobalt_wren.native.schema import validate_schema_value


@dataclass(frozen=True, slots=True)
class NativeLocalRunResult:
    output: Mapping[str, object]
    metadata: Mapping[str, object]
    status: str
    workflow_kind: str


def load_native_workflow(target: str) -> NativeWorkflow:
    module_name, separator, attribute_name = target.partition(":")
    if not separator or not module_name or not attribute_name:
        raise ValueError("Native target must use 'module:object' syntax")
    module = importlib.import_module(module_name)
    value = getattr(module, attribute_name)
    if not isinstance(value, NativeWorkflow):
        raise TypeError(f"{target!r} does not resolve to a NativeWorkflow")
    return value


def run_native_workflow(
    workflow: NativeWorkflow,
    input_payload: Mapping[str, object],
    *,
    workflow_kind: str = "local.native.workflow",
    config: Mapping[str, object] | None = None,
    run_id: int = 1,
) -> NativeLocalRunResult:
    plugin = workflow.plugin(
        plugin_name="local.native.workflow",
        workflow_kind=workflow_kind,
    )
    prepared = create_engine(
        dict(config or {"version": 1}),
        plugins=(plugin,),
        discover_plugins=False,
    ).prepare_workflow(workflow_kind)
    result = prepared.execute(
        dict(input_payload),
        context=WorkflowExecutionContext(run_id=run_id, thread_id=f"local-{run_id}"),
    )
    return NativeLocalRunResult(
        output=dict(result.output),
        metadata=dict(result.metadata),
        status=result.status,
        workflow_kind=workflow_kind,
    )


__all__ = ["NativeConfigurationError", "NativeLocalRunResult", "NativeValidationReport", "lint_native_requirements", "load_native_workflow", "run_native_workflow", "validate_native_workflow"]


class NativeConfigurationError(ValueError):
    def __init__(self, issues: list[str], suggestions: list[Mapping[str, object]]) -> None:
        self.issues = tuple(issues)
        self.suggestions = tuple(dict(item) for item in suggestions)
        super().__init__("Native configuration validation failed: " + "; ".join(issues))


@dataclass(frozen=True, slots=True)
class NativeValidationReport:
    workflow_name: str
    workflow_kind: str
    input_schema: Mapping[str, object] | None
    output_schema: Mapping[str, object] | None
    requirements: WorkflowRequirements
    warnings: tuple[Mapping[str, object], ...] = ()


def validate_native_workflow(
    workflow: NativeWorkflow,
    *,
    workflow_kind: str = "local.native.workflow",
    config: Mapping[str, object] | None = None,
    sample_input: Mapping[str, object] | None = None,
) -> NativeValidationReport:
    plugin = workflow.plugin(
        plugin_name="local.native.workflow", workflow_kind=workflow_kind
    )
    contribution = plugin.contributions.workflows[0]
    try:
        create_engine(
            dict(config or {"version": 1}),
            plugins=(plugin,),
            discover_plugins=False,
        ).prepare_workflow(workflow_kind)
    except Exception as exc:
        metadata = getattr(exc, "metadata", {})
        requirement_type = metadata.get("requirement_type") if isinstance(metadata, Mapping) else None
        requirement_name = metadata.get("requirement_name") if isinstance(metadata, Mapping) else None
        if isinstance(requirement_type, str) and isinstance(requirement_name, str):
            raise NativeConfigurationError(
                [f"missing {requirement_type} {requirement_name!r}"],
                [_configuration_suggestion(requirement_type, requirement_name)],
            ) from exc
        raise
    if sample_input is not None:
        validate_schema_value(dict(sample_input), workflow.input_schema, phase="input")
    return NativeValidationReport(
        workflow_name=workflow.name,
        workflow_kind=workflow_kind,
        input_schema=workflow.input_schema,
        output_schema=workflow.output_schema,
        requirements=contribution.definition.requirements,
        warnings=lint_native_requirements(workflow),
    )


def _configuration_suggestion(requirement_type: str, requirement_name: str) -> Mapping[str, object]:
    if requirement_type == "provider_profile":
        return {
            "message": f"Add provider profile {requirement_name!r}",
            "config": {
                "providers": {
                    "llm": {
                        requirement_name: {
                            "provider": "litellm",
                            "model": "replace-with-model",
                        }
                    }
                }
            },
        }
    if requirement_type == "tool":
        return {
            "message": f"Allow tool {requirement_name!r}",
            "config": {"tools": {"allowlist": [requirement_name]}},
        }
    if requirement_type == "artifact_store":
        return {
            "message": "Configure an artifact store",
            "config": {"stores": {"artifact": {"backend": "memory"}}},
        }
    if requirement_type == "event_sink":
        return {
            "message": f"Configure event sink {requirement_name!r}",
            "config": {"event_sinks": {requirement_name: {"backend": "replace-with-backend"}}},
        }
    return {"message": f"Configure {requirement_type} {requirement_name!r}", "config": {}}


def lint_native_requirements(workflow: NativeWorkflow) -> tuple[Mapping[str, object], ...]:
    """Best-effort source lint; explicit workflow requirements remain authoritative."""

    try:
        source = textwrap.dedent(inspect.getsource(workflow.function))
        tree = ast.parse(source)
    except (OSError, TypeError, SyntaxError):
        return ()
    parameters = list(inspect.signature(workflow.function).parameters)
    if not parameters:
        return ()
    context_name = parameters[0]
    declared = workflow.requirements
    warnings: list[Mapping[str, object]] = []
    seen: set[tuple[str, str]] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        path = _attribute_path(node.func)
        if path[:1] != (context_name,):
            continue
        if path[-2:] == ("llm", "complete"):
            profile_keyword = _keyword_value(node, "profile")
            if profile_keyword is None:
                profile = "default"
            elif isinstance(profile_keyword, ast.Constant) and isinstance(profile_keyword.value, str):
                profile = profile_keyword.value
            else:
                profile = None
            if profile is not None and profile not in declared.provider_profiles:
                _append_requirement_warning(warnings, seen, "provider_profile", profile, node.lineno)
        elif path[-2:] == ("tool", "run"):
            tool_name = _literal_argument(node, 1) or _literal_keyword(node, "tool_name")
            if tool_name is not None and tool_name not in declared.tools:
                _append_requirement_warning(warnings, seen, "tool", tool_name, node.lineno)
        elif path[-2:] == ("artifact", "write") and not declared.artifact_store:
            _append_requirement_warning(warnings, seen, "artifact_store", "artifact", node.lineno)
    return tuple(warnings)


def _attribute_path(node: ast.AST) -> tuple[str, ...]:
    parts: list[str] = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
    return tuple(reversed(parts))


def _keyword_value(node: ast.Call, name: str) -> ast.AST | None:
    for keyword in node.keywords:
        if keyword.arg == name:
            return keyword.value
    return None


def _literal_keyword(node: ast.Call, name: str) -> str | None:
    value = _keyword_value(node, name)
    if isinstance(value, ast.Constant) and isinstance(value.value, str):
        return value.value
    return None


def _literal_argument(node: ast.Call, index: int) -> str | None:
    if len(node.args) <= index:
        return None
    value = node.args[index]
    if isinstance(value, ast.Constant) and isinstance(value.value, str):
        return value.value
    return None


def _append_requirement_warning(
    warnings: list[Mapping[str, object]],
    seen: set[tuple[str, str]],
    requirement_type: str,
    requirement_name: str,
    line: int,
) -> None:
    identity = (requirement_type, requirement_name)
    if identity in seen:
        return
    seen.add(identity)
    warnings.append({
        "code": "NATIVE_REQUIREMENT_UNDECLARED",
        "message": f"Code appears to use {requirement_type} {requirement_name!r}, but it is not explicitly declared.",
        "requirement_type": requirement_type,
        "requirement_name": requirement_name,
        "line": line,
    })
