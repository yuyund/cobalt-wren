"""Complex LangGraph workflow for researching potential revenue opportunities."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
import operator
import time
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from cobalt_wren.api.stores import (
    ArtifactStore,
    ArtifactWriteRequest,
    CheckpointStore,
    CheckpointWriteRequest,
)
from cobalt_wren.api.workflow import WorkflowExecutionContext, WorkflowExecutionResult
from cobalt_wren.integrations.llm.base import LLMClient
from cobalt_wren.integrations.tools.base import ToolCallable


class ResearchState(TypedDict, total=False):
    theme: str
    constraints: list[str]
    max_opportunities: int
    queries: list[str]
    query: str
    search_results: Annotated[list[dict[str, object]], operator.add]
    candidates: list[dict[str, object]]
    candidate: dict[str, object]
    verified: Annotated[list[dict[str, object]], operator.add]
    ranked: list[dict[str, object]]
    retry_count: int
    max_retries: int
    minimum_sources: int
    wait_seconds: float
    needs_retry: bool
    report_markdown: str
    artifact_keys: list[str]
    saved_checkpoint_id: str
    requires_human_review: bool


@dataclass(frozen=True, slots=True)
class OpportunityResearchExecutable:
    llm: LLMClient
    search: ToolCallable
    artifact_store: ArtifactStore
    checkpoint_store: CheckpointStore
    default_max_retries: int = 1
    default_wait_seconds: float = 0.0
    minimum_sources: int = 4

    def execute(
        self,
        input_payload: Mapping[str, object],
        *,
        context: WorkflowExecutionContext,
    ) -> WorkflowExecutionResult:
        initial: ResearchState = {
            "theme": _required_text(input_payload, "theme"),
            "constraints": _string_list(input_payload.get("constraints", [])),
            "max_opportunities": _bounded_int(input_payload.get("max_opportunities", 5), 1, 10),
            "search_results": [],
            "verified": [],
            "retry_count": 0,
            "max_retries": _bounded_int(
                input_payload.get("max_retries", self.default_max_retries), 0, 3
            ),
            "minimum_sources": _bounded_int(
                input_payload.get("minimum_sources", self.minimum_sources), 1, 30
            ),
            "wait_seconds": max(
                0.0,
                min(_as_float(input_payload.get("wait_seconds"), self.default_wait_seconds), 5.0),
            ),
            "artifact_keys": [],
            "requires_human_review": False,
        }
        final = self._build_graph(context).compile(name="opportunity_research").invoke(initial)
        output = {
            "status": "needs_review" if final.get("requires_human_review") else "completed",
            "theme": final["theme"],
            "opportunities": list(final.get("ranked", [])),
            "report_markdown": final.get("report_markdown", ""),
            "artifact_keys": list(final.get("artifact_keys", [])),
            "checkpoint_id": final.get("saved_checkpoint_id", ""),
            "research_only": True,
        }
        return WorkflowExecutionResult(
            output=output,
            metadata={
                "search_result_count": len(final.get("search_results", [])),
                "retry_count": final.get("retry_count", 0),
                "candidate_count": len(final.get("ranked", [])),
                "patterns": [
                    "parallel-map",
                    "barrier-reduce",
                    "conditional-branch",
                    "bounded-loop",
                    "wait-backoff",
                    "parallel-verification",
                    "checkpoint",
                    "artifact",
                ],
            },
        )

    def _build_graph(self, context: WorkflowExecutionContext) -> StateGraph:
        def plan(state: ResearchState) -> ResearchState:
            parsed = _llm_json(
                self.llm,
                {
                    "task": "Create diverse web-search queries for revenue opportunity research.",
                    "theme": state["theme"],
                    "constraints": state.get("constraints", []),
                    "prior_result_count": len(state.get("search_results", [])),
                    "retry_count": state.get("retry_count", 0),
                    "required_output": {"queries": ["string"]},
                },
            )
            queries = _string_list(parsed.get("queries", []))[:6]
            if not queries:
                theme = state["theme"]
                queries = [
                    f"{theme} market demand pain points",
                    f"{theme} underserved customers recurring problems",
                    f"{theme} automation willingness to pay",
                ]
            return {"queries": list(dict.fromkeys(queries))}

        def route_search(state: ResearchState) -> list[Send]:
            return [Send("search", {**state, "query": query}) for query in state.get("queries", [])]

        def search_node(state: ResearchState) -> ResearchState:
            query = state["query"]
            result = self.search(
                query=query,
                language="auto",
                categories="general",
                limit=8,
            )
            rows = result.output if result.exit_code == 0 and isinstance(result.output, list) else []
            normalized = [
                {**dict(row), "query": query}
                for row in rows
                if isinstance(row, Mapping)
            ]
            _semantic_event(
                context,
                "opportunity.search.completed",
                {"query": query, "count": len(normalized)},
            )
            return {"search_results": normalized}

        def assess_evidence(state: ResearchState) -> ResearchState:
            unique_urls = {
                str(item.get("url", ""))
                for item in state.get("search_results", [])
                if item.get("url")
            }
            retry_count = state.get("retry_count", 0)
            needs_retry = (
                len(unique_urls) < state["minimum_sources"]
                and retry_count < state["max_retries"]
            )
            return {"needs_retry": needs_retry}

        def evidence_route(state: ResearchState) -> str:
            return "wait" if state.get("needs_retry", False) else "extract"

        def wait_node(state: ResearchState) -> ResearchState:
            delay = state.get("wait_seconds", 0.0) * (2 ** state.get("retry_count", 0))
            if delay:
                time.sleep(delay)
            return {
                "retry_count": state.get("retry_count", 0) + 1,
                "queries": [],
            }

        def extract(state: ResearchState) -> ResearchState:
            parsed = _llm_json(
                self.llm,
                {
                    "task": "Extract monetizable but non-executed business opportunity hypotheses from evidence.",
                    "theme": state["theme"],
                    "constraints": state.get("constraints", []),
                    "evidence": state.get("search_results", [])[:40],
                    "required_output": {
                        "opportunities": [
                            {
                                "title": "",
                                "customer": "",
                                "pain": "",
                                "offer": "",
                                "revenue_model": "",
                                "evidence_urls": [],
                                "confidence": 0.0,
                            }
                        ]
                    },
                },
            )
            raw_candidates = parsed.get("opportunities", [])
            candidates = [
                dict(item)
                for item in raw_candidates
                if isinstance(item, Mapping)
            ]
            return {"candidates": candidates[: state["max_opportunities"] * 2]}

        def route_verification(state: ResearchState) -> str | list[Send]:
            candidates = state.get("candidates", [])
            if not candidates:
                return "rank"
            return [
                Send("verify", {**state, "candidate": candidate})
                for candidate in candidates
            ]

        def verify(state: ResearchState) -> ResearchState:
            candidate = dict(state["candidate"])
            query = f"{candidate.get('title', '')} customer demand pricing alternatives"
            result = self.search(
                query=query,
                language="auto",
                categories="general",
                limit=5,
            )
            rows = result.output if result.exit_code == 0 and isinstance(result.output, list) else []
            validation_urls = [
                str(row.get("url"))
                for row in rows
                if isinstance(row, Mapping) and row.get("url")
            ]
            base_confidence = _as_float(candidate.get("confidence"), 0.5)
            score = min(1.0, base_confidence * 0.6 + min(len(validation_urls), 4) * 0.1)
            candidate.update(
                {
                    "validation_urls": validation_urls,
                    "score": round(score, 3),
                }
            )
            return {"verified": [candidate]}

        def rank(state: ResearchState) -> ResearchState:
            source = state.get("verified") or state.get("candidates", [])
            deduped: dict[str, dict[str, object]] = {}
            for item in source:
                title = str(item.get("title", "")).strip()
                if not title:
                    continue
                key = " ".join(title.lower().split())
                current = deduped.get(key)
                if current is None or _score(item) > _score(current):
                    deduped[key] = dict(item)
            ranked = sorted(deduped.values(), key=_score, reverse=True)[
                : state["max_opportunities"]
            ]
            requires_review = not ranked or _score(ranked[0]) < 0.55
            return {
                "ranked": ranked,
                "requires_human_review": requires_review,
            }

        def report(state: ResearchState) -> ResearchState:
            markdown = _llm_text(
                self.llm,
                {
                    "task": "Write a concise cited Markdown research report. Do not claim guaranteed profit and do not execute any action.",
                    "theme": state["theme"],
                    "constraints": state.get("constraints", []),
                    "opportunities": state.get("ranked", []),
                    "sections": [
                        "Executive summary",
                        "Ranked opportunities",
                        "Evidence",
                        "Risks and invalidation tests",
                        "Suggested next research",
                    ],
                },
            )
            return {"report_markdown": markdown.strip() or _fallback_report(state)}

        def persist(state: ResearchState) -> ResearchState:
            run_id: int | str = (
                context.run_id
                if context.run_id is not None
                else (context.thread_id or "opportunity-research")
            )
            base = f"opportunity-research/{run_id}"
            report_artifact = self.artifact_store.put(
                ArtifactWriteRequest(
                    run_id=run_id,
                    storage_key=f"{base}/report.md",
                    body=state["report_markdown"].encode("utf-8"),
                    name="opportunity research report",
                    kind="report",
                    content_type="text/markdown",
                    metadata={"workflow": "opportunity.research"},
                )
            )
            structured = json.dumps(
                {
                    "theme": state["theme"],
                    "opportunities": state.get("ranked", []),
                    "research_only": True,
                },
                ensure_ascii=False,
                sort_keys=True,
            ).encode("utf-8")
            json_artifact = self.artifact_store.put(
                ArtifactWriteRequest(
                    run_id=run_id,
                    storage_key=f"{base}/opportunities.json",
                    body=structured,
                    name="opportunity hypotheses",
                    kind="dataset",
                    content_type="application/json",
                    metadata={"workflow": "opportunity.research"},
                )
            )
            checkpoint_body = json.dumps(
                {
                    "theme": state["theme"],
                    "ranked": state.get("ranked", []),
                    "retry_count": state.get("retry_count", 0),
                },
                ensure_ascii=False,
                sort_keys=True,
            ).encode("utf-8")
            checkpoint = self.checkpoint_store.save(
                CheckpointWriteRequest(
                    run_id=run_id,
                    checkpoint_id="research-complete",
                    body=checkpoint_body,
                    serializer_name="json",
                    serializer_version=1,
                    content_type="application/json",
                    checkpoint_namespace="opportunity-research",
                    metadata={
                        "workflow": "opportunity.research",
                        "stage": "complete",
                    },
                )
            )
            return {
                "artifact_keys": [
                    report_artifact.storage_key,
                    json_artifact.storage_key,
                ],
                "saved_checkpoint_id": checkpoint.checkpoint_id,
            }

        graph = StateGraph(ResearchState)
        graph.add_node("plan", plan)
        graph.add_node("search", search_node)
        graph.add_node("assess", assess_evidence)
        graph.add_node("wait", wait_node)
        graph.add_node("extract", extract)
        graph.add_node("verify", verify)
        graph.add_node("rank", rank)
        graph.add_node("report", report)
        graph.add_node("persist", persist)
        graph.add_edge(START, "plan")
        graph.add_conditional_edges("plan", route_search, ["search"])
        graph.add_edge("search", "assess")
        graph.add_conditional_edges(
            "assess",
            evidence_route,
            {"wait": "wait", "extract": "extract"},
        )
        graph.add_edge("wait", "plan")
        graph.add_conditional_edges("extract", route_verification, ["verify", "rank"])
        graph.add_edge("verify", "rank")
        graph.add_edge("rank", "report")
        graph.add_edge("report", "persist")
        graph.add_edge("persist", END)
        return graph


def _llm_json(llm: LLMClient, payload: Mapping[str, object]) -> dict[str, Any]:
    result = llm.complete(
        [
            {"role": "system", "content": "Return only valid JSON."},
            {
                "role": "user",
                "content": json.dumps(payload, ensure_ascii=False, default=str),
            },
        ]
    )
    text = result.content.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].lstrip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return dict(parsed) if isinstance(parsed, Mapping) else {}


def _llm_text(llm: LLMClient, payload: Mapping[str, object]) -> str:
    return llm.complete(
        [
            {
                "role": "system",
                "content": "Produce a factual research report with explicit uncertainty.",
            },
            {
                "role": "user",
                "content": json.dumps(payload, ensure_ascii=False, default=str),
            },
        ]
    ).content


def _semantic_event(
    context: WorkflowExecutionContext,
    kind: str,
    payload: Mapping[str, object],
) -> None:
    callback = getattr(context.event_sink, "semantic_event", None)
    if callable(callback):
        callback(context.run_id or 0, kind, payload=dict(payload))


def _required_text(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} is required")
    return value.strip()


def _string_list(value: object) -> list[str]:
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _bounded_int(value: object, minimum: int, maximum: int) -> int:
    return min(max(_as_int(value, minimum), minimum), maximum)


def _score(item: Mapping[str, object]) -> float:
    return _as_float(item.get("score", item.get("confidence", 0.0)), 0.0)


def _fallback_report(state: ResearchState) -> str:
    lines = [
        f"# Opportunity research: {state['theme']}",
        "",
        "> Research hypotheses only. No execution or guaranteed-profit claim.",
        "",
    ]
    for index, item in enumerate(state.get("ranked", []), start=1):
        lines.extend(
            [
                f"## {index}. {item.get('title', 'Untitled opportunity')}",
                "",
                str(item.get("offer", item.get("pain", ""))),
                "",
            ]
        )
    return "\n".join(lines)


def _as_int(value: object, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, (float, str)):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default
    return default


def _as_float(value: object, default: float) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    return default
