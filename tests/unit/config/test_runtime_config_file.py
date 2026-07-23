from pathlib import Path

from django.test import override_settings

from langgraph_automation.apps.automation.services.runtime import load_deployment_package_config_from_settings


def test_runtime_loads_explicit_json_config_file(tmp_path: Path) -> None:
    path = tmp_path / "automation.json"
    path.write_text('{"version": 1, "environment": "file"}')
    with override_settings(LANGGRAPH_AUTOMATION_CONFIG_FILE=str(path), LANGGRAPH_AUTOMATION='{"version": 1, "environment": "env"}'):
        assert load_deployment_package_config_from_settings()["environment"] == "file"
