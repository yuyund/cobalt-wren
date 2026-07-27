# Native Selection Guide

Use Native for bounded Python business pipelines that run from seconds to tens of minutes and can restart from the beginning after process failure. Native is appropriate for sequential work, ordinary Python branching, bounded loops, APIs, LLM calls, tools, artifacts, retry, timeout, progress, and metrics.

Use LangGraph when checkpoint recovery, interrupt/resume, durable waiting, cycles, stateful subgraphs, time travel, or agent memory are primary requirements.

Use a plain executable when adapting an existing object with an `execute` or `invoke` capability and Native authoring helpers add little value. Use another integration when its domain or event model is the natural ownership boundary.

Native does not promise arbitrary Python state serialization, exactly-once side effects, distributed fan-out, or forced termination of timed-out synchronous threads.
