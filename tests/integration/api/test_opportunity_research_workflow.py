from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).parents[3]
EXAMPLE_SRC = ROOT / "packages" / "opportunity_research_workflow" / "src"
sys.path.insert(0, str(EXAMPLE_SRC))

from opportunity_research_workflow import WORKFLOW_KIND, create_plugin  # noqa: E402
from langgraph_automation.apps.automation.models.run import Run, RunStatus  # noqa: E402
from langgraph_automation.apps.automation.models.workflow import Workflow  # noqa: E402
from langgraph_automation.apps.automation.services import runs as run_services  # noqa: E402
from langgraph_automation.apps.automation.services import runtime as runtime_module  # noqa: E402
from langgraph_automation.integrations.tools.base import ToolResult  # noqa: E402
from tests.support.recording_event_sink import RecordingEventSink  # noqa: E402


class FakeSearch:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def __call__(self, *, query: str, **_: object) -> ToolResult:
        self.calls.append(query)
        rows = [
            {
                "title": f"Evidence {index}",
                "url": f"https://example.test/{len(self.calls)}/{index}",
                "snippet": "Recurring manual work and stated budget.",
                "score": 1.0,
            }
            for index in range(3)
        ]
        return ToolResult(output=rows, output_summary=f"{len(rows)} results")


def _fake_litellm_completion(**kwargs):
    payload = json.loads(kwargs["messages"][-1]["content"])
    task = payload.get("task", "")
    if "search queries" in task:
        content = json.dumps(
            {
                "queries": [
                    "invoice reconciliation pain",
                    "small clinic scheduling automation",
                    "compliance reporting backlog",
                ]
            }
        )
    elif "Extract monetizable" in task:
        content = json.dumps(
            {
                "opportunities": [
                    {
                        "title": "Invoice exception triage service",
                        "customer": "small accounting teams",
                        "pain": "manual exception review",
                        "offer": "human-in-the-loop automation",
                        "revenue_model": "monthly subscription",
                        "evidence_urls": ["https://example.test/source"],
                        "confidence": 0.8,
                    },
                    {
                        "title": "Clinic no-show reduction assistant",
                        "customer": "small clinics",
                        "pain": "lost appointments",
                        "offer": "reminder and waitlist automation",
                        "revenue_model": "per-location subscription",
                        "evidence_urls": ["https://example.test/clinic"],
                        "confidence": 0.72,
                    },
                ]
            }
        )
    else:
        content = (
            "# Revenue Opportunity Research\n\n"
            "## Ranked opportunities\n\n"
            "Evidence-backed hypotheses requiring human validation."
        )
    return {
        "choices": [{"message": {"content": content}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 10},
        "model": "fake-research-model",
    }


@pytest.mark.django_db
def test_django_control_plane_executes_complex_external_research_workflow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_search = FakeSearch()
    plugin = create_plugin(search_factory=lambda _config: fake_search)
    sink = RecordingEventSink()
    monkeypatch.setattr(runtime_module, "build_event_sink", lambda _run: sink)
    monkeypatch.setattr(
        "langgraph_automation.integrations.llm.litellm_client.litellm.completion",
        _fake_litellm_completion,
    )
    services = runtime_module.build_run_execution_services(
        {
            "version": 1,
            "environment": "test",
            "providers": {
                "research": {"provider": "litellm", "model": "fake-model"}
            },
            "tools": {
                "allowlist": ["searxng.search"],
                "configs": {
                    "searxng.search": {"base_url": "http://searxng.test"}
                },
            },
            "stores": {
                "artifact": {"backend": "memory"},
                "checkpoint": {"backend": "memory"},
            },
        },
        plugins=(plugin,),
        discover_plugins=False,
    )
    workflow = Workflow.objects.create(
        name="opportunity-research",
        definition_payload={
            "workflow": {
                "kind": WORKFLOW_KIND,
                "config": {
                    "minimum_sources": 4,
                    "max_retries": 1,
                    "wait_seconds": 0,
                },
            }
        },
    )
    run = Run.objects.create(
        workflow=workflow,
        name="research-run",
        input_payload={
            "theme": "small B2B automation opportunities in Japan",
            "constraints": ["low initial capital", "solo operator"],
            "max_opportunities": 3,
        },
    )

    result = run_services.start_run(run=run, services=services)
    result.run.refresh_from_db()

    assert result.run.status == RunStatus.SUCCEEDED
    assert result.execution_result is not None
    output = result.execution_result.output_payload
    assert output["research_only"] is True
    assert output["status"] == "completed"
    assert len(output["opportunities"]) == 2
    assert len(output["artifact_keys"]) == 2
    assert output["checkpoint_id"] == "research-complete"
    assert len(fake_search.calls) >= 5
    assert any(
        event.kind == "opportunity.search.completed"
        for event in sink.run_events
    )
    assert result.run.output_payload == result.output_payload
