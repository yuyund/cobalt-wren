from __future__ import annotations

from cobalt_wren.api.engine import create_engine
from cobalt_wren.api.workflow import WorkflowExecutionContext
from cobalt_wren.native.definitions import step
from cobalt_wren.native.recipes import sequential_workflow


def test_sequential_workflow_passes_each_result_to_the_next_step() -> None:
    recipe = sequential_workflow(
        name="Sequential recipe",
        steps=(
            step("extract", lambda request: str(request["message"]).strip()),
            step("normalize", lambda value: value.upper()),
        ),
    )
    plugin = recipe.plugin(
        plugin_name="test.native.recipe",
        workflow_kind="test.native.recipe",
    )
    prepared = create_engine(
        {"version": 1},
        plugins=(plugin,),
        discover_plugins=False,
    ).prepare_workflow("test.native.recipe")

    result = prepared.execute(
        {"message": " hello "},
        context=WorkflowExecutionContext(run_id=901),
    )

    assert result.output == {"result": "HELLO"}
    assert result.metadata["step_count"] == 2
