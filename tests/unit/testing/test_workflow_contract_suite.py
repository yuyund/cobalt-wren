from pathlib import Path
import sys

ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(ROOT / "packages" / "plain_python_workflow" / "src"))

from plain_python_workflow import WORKFLOW_KIND, create_plugin  # noqa: E402
from cobalt_wren.testing import WorkflowContractSuite  # noqa: E402


def test_suite_validates_reference_plain_workflow(tmp_path) -> None:
    suite = WorkflowContractSuite(
        plugin_factory=create_plugin,
        workflow_kind=WORKFLOW_KIND,
        package_config={"version": 1, "stores": {"artifact": {"backend": "filesystem", "config": {"root": str(tmp_path / "artifacts")}}, "checkpoint": {"backend": "filesystem", "config": {"root": str(tmp_path / "checkpoints")}}}},
    )
    suite.assert_declared()
    suite.assert_framework_neutral_definition()
    suite.assert_buildable()
    output = suite.assert_pause_resume_round_trip(input_payload={"subject": "Contract", "message": "Round trip"}, resume_payload={"action": "confirm"})
    assert output["decision"] == "confirmed"
