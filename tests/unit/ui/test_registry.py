"""UI registry tests."""

from __future__ import annotations

from langgraph_automation.apps.automation.ui.registry import get_model_ui_config


def test_runs_ui_actions_do_not_include_resume() -> None:
    config = get_model_ui_config('runs')

    assert config is not None
    assert [action.name for action in config.actions] == ['start', 'cancel', 'retry']
