"""Documentation guards for the use-case-driven Native Authoring direction."""

from __future__ import annotations

from pathlib import Path


DESIGN = Path(
    "docs/workflows/authoring/NATIVE_AUTHORING_USE_CASE_DESIGN.md"
)
AUTHOR_GUIDE = Path("docs/workflows/authoring/WORKFLOW_AUTHOR_GUIDE.md")
OSS_DESIGN = Path(
    "docs/architecture/design/OSS_NEUTRAL_WORKFLOW_INTEGRATION.md"
)
CONTRACTS = Path("docs/contracts/core/CONTRACTS.md")
ROADMAP = Path("docs/roadmap/milestones/ROADMAP.md")


def test_native_authoring_use_case_design_covers_primary_experience() -> None:
    text = DESIGN.read_text(encoding="utf-8")

    for required in (
        "ordinary Python control flow",
        "explicit named step boundaries",
        "Sequential business pipeline",
        "Conditional business routing",
        "Bounded iteration",
        "External API with retry and timeout",
        "LLM and tool workflow",
        "Artifact-producing workflow",
        "Failure and cancellation",
        "External package reuse",
        "Progressive Disclosure Model",
        "MVP Acceptance Scenarios",
    ):
        assert required in text


def test_native_authoring_design_keeps_langgraph_as_advanced_durable_path() -> None:
    text = DESIGN.read_text(encoding="utf-8")

    for required in (
        "Checkpoint recovery",
        "Interrupt/resume",
        "Durable waiting",
        "Time travel and fork",
        "Graph cycle and agent loop",
        "Stateful subgraph",
        "Use LangGraph when",
    ):
        assert required in text

    assert "Native Authoring is not a reduced LangGraph implementation" in text
    assert "LangGraph remains the recommended integration" in text


def test_native_authoring_mvp_non_goals_are_explicit() -> None:
    text = DESIGN.read_text(encoding="utf-8")

    for non_goal in (
        "checkpoint-based continuation from an arbitrary step",
        "durable timers or multi-day waiting",
        "deterministic replay of arbitrary Python",
        "time travel or state fork",
        "exactly-once side effects",
        "distributed fan-out at arbitrary scale",
    ):
        assert non_goal in text


def test_native_authoring_p2_policy_core_is_documented() -> None:
    design = DESIGN.read_text(encoding="utf-8")
    contracts = CONTRACTS.read_text(encoding="utf-8")

    for required in (
        "Implemented NATIVE-P2 Policy Core",
        "RetryPolicy",
        "timeout_seconds",
        "occurrence_key",
        "Sync callables run in a worker thread",
        "1,000 step occurrences",
    ):
        assert required in design
    assert "Native Authoring P2 Policy Contract" in contracts
    assert "Native Examples Boundary" in design
    assert "Native Examples Contract" in contracts


def test_native_authoring_direction_is_synchronized_across_normative_docs() -> None:
    author_guide = AUTHOR_GUIDE.read_text(encoding="utf-8")
    oss_design = OSS_DESIGN.read_text(encoding="utf-8")
    contracts = CONTRACTS.read_text(encoding="utf-8")
    roadmap = ROADMAP.read_text(encoding="utf-8")

    assert "Native Authoring Direction" in author_guide
    assert "Current Native P1 Surface" in author_guide
    assert "NATIVE_AUTHORING_USE_CASE_DESIGN.md" in author_guide
    assert "LangGraph is not the Native MVP backend" in oss_design
    assert "Native Authoring Direction Contract" in contracts
    assert "Native Authoring P1 Contract" in contracts
    assert "Native Authoring P2 Policy Contract" in contracts
    assert "Native Design Block NATIVE-D1" in roadmap
    assert "Native block NATIVE-P1" in roadmap
    assert "Native block NATIVE-P2A" in roadmap
    assert "status: complete" in roadmap
    assert "Next Native block, NATIVE-P2B" in roadmap
