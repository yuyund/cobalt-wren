"""Deployment engine cache generation and reload tests."""
from __future__ import annotations

from threading import Event, Thread

import pytest

from langgraph_automation.api.engine import EnginePreparedWorkflow
from langgraph_automation.api.errors import FrameworkError
from langgraph_automation.apps.automation.services import runtime as runtime_module
from langgraph_automation.apps.automation.services.runtime import DeploymentEngineOwner
from langgraph_automation.apps.automation.services.workflow_reference import WorkflowReference


class FakeEngine:
    def __init__(self, label: str) -> None:
        self.label = label

    def prepare_workflow(self, kind: str, *, config=None) -> EnginePreparedWorkflow:
        label = self.label
        return EnginePreparedWorkflow(
            kind=kind,
            executable=lambda _payload: {"engine": label, "config": dict(config or {})},
        )


def test_lazy_engine_starts_at_generation_zero_and_initializes_generation_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created: list[FakeEngine] = []
    monkeypatch.setattr(
        runtime_module,
        "create_engine",
        lambda *_args, **_kwargs: created.append(FakeEngine("one")) or created[-1],
    )
    owner = DeploymentEngineOwner(raw_config={"version": 1}, discover_plugins=False)

    assert owner.generation.generation == 0
    engine = owner.get_engine()

    assert engine is created[0]
    assert owner.generation.generation == 1
    assert len(owner.generation.signature) == 64


def test_same_identity_is_noop_but_force_rebuilds(monkeypatch: pytest.MonkeyPatch) -> None:
    created: list[FakeEngine] = []

    def factory(*_args, **_kwargs):
        engine = FakeEngine(str(len(created) + 1))
        created.append(engine)
        return engine

    monkeypatch.setattr(runtime_module, "create_engine", factory)
    owner = DeploymentEngineOwner(raw_config={"version": 1}, discover_plugins=False)
    first = owner.get_engine()

    unchanged = owner.reconfigure(
        raw_config={"version": 1}, discover_plugins=False
    )
    assert unchanged.generation == 1
    assert owner.get_engine() is first
    assert len(created) == 1

    rebuilt = owner.reconfigure(
        raw_config={"version": 1}, discover_plugins=False, force=True
    )
    assert rebuilt.generation == 2
    assert owner.get_engine() is created[1]


def test_successful_reconfigure_swaps_engine_and_marks_prepared_generation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created: list[FakeEngine] = []

    def factory(config, **_kwargs):
        engine = FakeEngine(str(config["environment"]))
        created.append(engine)
        return engine

    monkeypatch.setattr(runtime_module, "create_engine", factory)
    owner = DeploymentEngineOwner(
        raw_config={"version": 1, "environment": "old"}, discover_plugins=False
    )
    old_prepared = owner.prepare(WorkflowReference(kind="acme.review"))

    generation = owner.reconfigure(
        raw_config={"version": 1, "environment": "new"},
        discover_plugins=False,
    )
    new_prepared = owner.prepare(WorkflowReference(kind="acme.review"))

    assert generation.generation == 2
    assert old_prepared.engine_generation == 1
    assert new_prepared.engine_generation == 2
    assert old_prepared.engine_signature != new_prepared.engine_signature
    assert old_prepared.execute({}).output["engine"] == "old"
    assert new_prepared.execute({}).output["engine"] == "new"


def test_failed_reconfigure_preserves_last_known_good() -> None:
    owner = DeploymentEngineOwner(raw_config={"version": 1}, discover_plugins=False)
    original = owner.get_engine()
    before = owner.generation

    with pytest.raises(FrameworkError):
        owner.reconfigure(
            raw_config={"version": "invalid"}, discover_plugins=False
        )

    assert owner.get_engine() is original
    assert owner.generation == before
    assert owner.raw_config == {"version": 1}


def test_existing_engine_remains_available_while_candidate_builds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    build_started = Event()
    allow_build = Event()
    old = FakeEngine("old")
    new = FakeEngine("new")
    calls = 0

    def factory(config, **_kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            return old
        build_started.set()
        assert allow_build.wait(timeout=5)
        return new

    monkeypatch.setattr(runtime_module, "create_engine", factory)
    owner = DeploymentEngineOwner(raw_config={"version": 1}, discover_plugins=False)
    assert owner.get_engine() is old
    result: list[object] = []

    thread = Thread(
        target=lambda: result.append(
            owner.reconfigure(
                raw_config={"version": 1, "environment": "new"},
                discover_plugins=False,
            )
        )
    )
    thread.start()
    assert build_started.wait(timeout=5)

    assert owner.get_engine() is old
    assert owner.generation.generation == 1
    allow_build.set()
    thread.join(timeout=5)

    assert not thread.is_alive()
    assert owner.get_engine() is new
    assert owner.generation.generation == 2


def test_discovery_signature_change_triggers_reload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    signatures = iter(((("a", "pkg:a", "pkg", "1"),), (("a", "pkg:a", "pkg", "2"),)))
    current = [next(signatures)]
    created: list[FakeEngine] = []
    monkeypatch.setattr(
        runtime_module,
        "_installed_plugin_entry_point_signature",
        lambda: current[0],
    )
    monkeypatch.setattr(
        runtime_module,
        "create_engine",
        lambda *_args, **_kwargs: created.append(FakeEngine(str(len(created)))) or created[-1],
    )
    owner = DeploymentEngineOwner(raw_config={"version": 1}, discover_plugins=True)
    owner.get_engine()
    current[0] = next(signatures)

    generation = owner.reconfigure(
        raw_config={"version": 1}, discover_plugins=True
    )

    assert generation.generation == 2
    assert len(created) == 2
