"""Contract-test kit for independently distributed workflows."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import json

from langgraph_automation.api.engine import AutomationEngine, create_engine
from langgraph_automation.api.plugins import Plugin
from langgraph_automation.api.workflow import WorkflowDefinition, WorkflowExecutionContext, WorkflowResumeRequest


def assert_plugin_declares_workflow(plugin: Plugin, workflow_kind: str) -> WorkflowDefinition:
    matches = [item.definition for item in plugin.contributions.workflows if item.kind == workflow_kind]
    assert len(matches) == 1, f"expected exactly one workflow contribution for {workflow_kind!r}"
    definition = matches[0]
    assert definition.kind == workflow_kind
    assert definition.metadata.name.strip()
    assert callable(definition.build)
    return definition


def assert_workflow_definition_is_framework_neutral(definition: WorkflowDefinition) -> None:
    rendered = repr((definition.kind, definition.metadata.name, definition.input_schema, definition.output_schema, definition.extra))
    assert "langgraph.graph" not in rendered
    assert "StateGraph" not in rendered
    assert "CompiledStateGraph" not in rendered


def assert_prepared_workflow_executes(engine: AutomationEngine, workflow_kind: str, *, workflow_config: Mapping[str, object], input_payload: Mapping[str, object], required_output_fields: tuple[str, ...] = ()) -> Mapping[str, object]:
    prepared = engine.prepare_workflow(workflow_kind, config=workflow_config)
    result = prepared.execute(input_payload, context=WorkflowExecutionContext(thread_id="contract-test"))
    output = dict(result.output)
    for field in required_output_fields:
        assert field in output, f"workflow output is missing required field {field!r}"
    return output


@dataclass(frozen=True, slots=True)
class WorkflowContractSuite:
    plugin_factory: Callable[[], Plugin]
    workflow_kind: str
    package_config: Mapping[str, object] | None = None

    def plugin(self) -> Plugin:
        plugin = self.plugin_factory()
        assert isinstance(plugin, Plugin)
        return plugin

    def definition(self) -> WorkflowDefinition:
        return assert_plugin_declares_workflow(self.plugin(), self.workflow_kind)

    def engine(self) -> AutomationEngine:
        return create_engine(self.package_config or {"version": 1}, plugins=(self.plugin(),), discover_plugins=False)

    def assert_declared(self) -> WorkflowDefinition:
        return self.definition()

    def assert_framework_neutral_definition(self) -> None:
        assert_workflow_definition_is_framework_neutral(self.definition())

    def assert_buildable(self, *, workflow_config: Mapping[str, object] | None = None) -> object:
        return self.engine().prepare_workflow(self.workflow_kind, config=workflow_config or {})

    def assert_executes(self, *, input_payload: Mapping[str, object], workflow_config: Mapping[str, object] | None = None, required_output_fields: tuple[str, ...] = ()) -> Mapping[str, object]:
        output = assert_prepared_workflow_executes(self.engine(), self.workflow_kind, workflow_config=workflow_config or {}, input_payload=input_payload, required_output_fields=required_output_fields)
        json.dumps(output)
        return output

    def assert_pause_resume_round_trip(self, *, input_payload: Mapping[str, object], resume_payload: Mapping[str, object], workflow_config: Mapping[str, object] | None = None) -> Mapping[str, object]:
        engine = self.engine()
        context = WorkflowExecutionContext(run_id=1, thread_id="contract-resume")
        first = engine.prepare_workflow(self.workflow_kind, config=workflow_config or {}).execute(input_payload, context=context)
        assert first.status == "paused"
        checkpoint_id = first.output.get("checkpoint_id")
        prepared_again = engine.prepare_workflow(self.workflow_kind, config=workflow_config or {})
        result = prepared_again.resume(WorkflowResumeRequest(value=resume_payload, checkpoint_id=checkpoint_id if isinstance(checkpoint_id, str) else None), context=context)
        assert result.status == "completed"
        output = dict(result.output)
        json.dumps(output)
        return output

    def assert_output_json_safe(self, output: Mapping[str, object]) -> None:
        json.dumps(dict(output))
