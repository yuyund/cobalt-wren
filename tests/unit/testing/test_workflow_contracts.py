from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).parents[3]
EXAMPLE_SRC = ROOT / "packages" / "opportunity_research_workflow" / "src"
sys.path.insert(0, str(EXAMPLE_SRC))

from opportunity_research_workflow import WORKFLOW_KIND, create_plugin  # noqa: E402
from cobalt_wren.testing import (  # noqa: E402
    assert_plugin_declares_workflow,
    assert_workflow_definition_is_framework_neutral,
)


def test_example_satisfies_external_workflow_definition_contract() -> None:
    definition = assert_plugin_declares_workflow(create_plugin(), WORKFLOW_KIND)
    assert_workflow_definition_is_framework_neutral(definition)
    assert definition.metadata.metadata["research_only"] is True
    assert definition.extra["safety"]["research_only"] is True
