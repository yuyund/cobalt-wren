"""Small contract-test kit for external workflow packages."""
from __future__ import annotations

from collections.abc import Mapping

from langgraph_automation.api.engine import AutomationEngine
from langgraph_automation.api.plugins import Plugin
from langgraph_automation.api.workflow import (
    WorkflowDefinition,
    WorkflowExecutionContext,
)


def assert_plugin_declares_workflow(
    plugin: Plugin,
    workflow_kind: str,
) -> WorkflowDefinition:
    matches = [
        item.definition
        for item in plugin.contributions.workflows
        if item.kind == workflow_kind
    ]
    assert len(matches) == 1, (
        f"expected exactly one workflow contribution for {workflow_kind!r}"
    )
    definition = matches[0]
    assert definition.kind == workflow_kind
    assert definition.metadata.name.strip()
    assert callable(definition.build)
    return definition


def assert_workflow_definition_is_framework_neutral(
    definition: WorkflowDefinition,
) -> None:
    public_values = (
        definition.kind,
        definition.metadata.name,
        definition.input_schema,
        definition.output_schema,
        definition.extra,
    )
    rendered = repr(public_values)
    assert "langgraph.graph" not in rendered
    assert "StateGraph" not in rendered
    assert "CompiledStateGraph" not in rendered


def assert_prepared_workflow_executes(
    engine: AutomationEngine,
    workflow_kind: str,
    *,
    workflow_config: Mapping[str, object],
    input_payload: Mapping[str, object],
    required_output_fields: tuple[str, ...] = (),
) -> Mapping[str, object]:
    prepared = engine.prepare_workflow(workflow_kind, config=workflow_config)
    result = prepared.execute(
        input_payload,
        context=WorkflowExecutionContext(thread_id="contract-test"),
    )
    output = dict(result.output)
    for field in required_output_fields:
        assert field in output, f"workflow output is missing required field {field!r}"
    return output
