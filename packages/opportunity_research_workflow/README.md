# Opportunity Research Workflow

An independently packaged workflow that searches for potential revenue opportunities and generates a cited research report. It performs research and recommendation only. It does not purchase, post, contact prospects, transfer money, create accounts, or execute a business action.

## Included workflow patterns

- LLM-based query planning, hypothesis extraction, and report generation
- SearXNG-compatible web search
- parallel search fan-out and barrier aggregation
- bounded retry loop with configurable waiting/backoff
- conditional branching for insufficient evidence
- parallel candidate verification
- deduplication, scoring, ranking, and graceful fallback
- checkpoint snapshots and Markdown/JSON artifacts

## Deployment configuration

```json
{
  "version": 1,
  "providers": {
    "research": {"provider": "litellm", "model": "openai/your-model"}
  },
  "tools": {
    "allowlist": ["searxng.search"],
    "configs": {
      "searxng.search": {
        "base_url": "http://searxng:8080",
        "timeout_seconds": 10,
        "max_results": 8
      }
    }
  },
  "stores": {
    "artifact": {"backend": "memory"},
    "checkpoint": {"backend": "memory"}
  }
}
```
