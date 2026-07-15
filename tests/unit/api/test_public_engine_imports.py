"""Public engine facade import coverage."""

from __future__ import annotations


def test_public_engine_api_exports() -> None:
    import langgraph_automation.api.engine as engine_api

    from langgraph_automation.api.engine import AutomationEngine, EnginePreparedWorkflow, create_engine

    assert create_engine is not None
    assert AutomationEngine is not None
    assert EnginePreparedWorkflow is not None
    assert set(engine_api.__all__) == {"EnginePreparedWorkflow", "AutomationEngine", "create_engine"}
    assert not hasattr(engine_api, "run_workflow")


def test_public_api_package_does_not_re_export_engine_symbols() -> None:
    import langgraph_automation.api as api_package

    assert not hasattr(api_package, "create_engine")
    assert not hasattr(api_package, "AutomationEngine")
    assert not hasattr(api_package, "EnginePreparedWorkflow")
