---
type: guide
status: current
authority: explanatory
summary: External complex workflow example that researches evidence-backed revenue opportunities using LLM and SearXNG.
code_refs:
  - packages/opportunity_research_workflow
  - src/langgraph_automation/py.typed
  - src/langgraph_automation/testing
  - pyproject.toml
  - .github/workflows/ci.yml
test_refs:
  - tests/integration/api/test_opportunity_research_workflow.py
  - tests/integration/api/test_opportunity_research_distribution.py
  - tests/unit/testing/test_workflow_contracts.py
  - tests/unit/testing/test_searxng_search_tool.py
verified:
  date: 2026-07-23
  commit: WORKTREE
  base_commit: cf9f744
  method:
    - code-and-test-review
---
# Opportunity Research Workflow

This independently packaged example tests the platform as a workflow execution control plane rather than a LangGraph wrapper.

Its internal graph uses:

- LLM planning and synthesis;
- SearXNG-compatible search;
- parallel search fan-out and barrier aggregation;
- bounded retry loops with wait/backoff;
- conditional routing for insufficient evidence;
- parallel candidate verification;
- deduplication, scoring, and ranking;
- checkpoint and artifact persistence;
- degraded fallback report generation.

The workflow only researches and reports possible revenue opportunities. It does not execute purchases, payments, outreach, account creation, publishing, or other business actions.

The external distribution owns its graph state, prompts, ranking policy, SearXNG client, and report schema. The foundation owns plugin discovery, provider/tool/store resolution, lifecycle, safe result persistence, and control-plane execution.
