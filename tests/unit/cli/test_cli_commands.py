from __future__ import annotations

import json
from pathlib import Path

import pytest

from langgraph_automation.cli.main import main


def test_plugins_list_outputs_json(capsys) -> None:
    assert main(["plugins", "list"]) == 0
    assert isinstance(json.loads(capsys.readouterr().out), list)


@pytest.mark.django_db
def test_doctor_reports_database_and_migrations(capsys) -> None:
    assert main(["doctor"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    assert {item["name"] for item in payload["checks"]} >= {"database", "migrations", "plugins", "runtime"}


def test_config_file_is_selected_before_django_startup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "config.json"
    path.write_text('{"version": 1, "environment": "cli-test"}')
    monkeypatch.delenv("LANGGRAPH_AUTOMATION_CONFIG_FILE", raising=False)
    from langgraph_automation.cli.main import _configure_environment
    _configure_environment(path)
    assert Path(__import__("os").environ["LANGGRAPH_AUTOMATION_CONFIG_FILE"]) == path.resolve()
