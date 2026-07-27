---
type: audit
status: current
authority: normative
summary: Reproducible local baseline for engine creation, workflow preparation, and executable invocation overhead.
code_refs:
  - scripts/benchmark_runtime.py
  - config/runtime-performance-baseline.json
  - src/cobalt_wren/api/engine.py
  - src/cobalt_wren/workflows/prepare.py
test_refs:
  - tests/unit/architecture/test_runtime_benchmark.py
  - tests/integration/api/test_public_execution_persistence.py
verified:
  date: 2026-07-23
  commit: WORKTREE
  base_commit: ed0702a
  method:
    - local-performance-sampling
---
# Runtime Performance Baseline

The benchmark measures three framework-controlled operations with the external workflow fixture:

1. package engine creation without entry-point discovery;
2. workflow requirement checking and executable preparation;
3. framework-neutral executable invocation.

`config/runtime-performance-baseline.json` records 25 local samples using monotonic nanosecond timing. The values are observational, not universal service-level objectives. CI executes a five-iteration schema and execution smoke test but does not fail on wall-clock thresholds because shared runners are not stable benchmark hosts.

A reviewed performance change may regenerate the baseline with:

```bash
venv/bin/python scripts/benchmark_runtime.py \
  --iterations 25 \
  --output config/runtime-performance-baseline.json
```

Comparisons must use the same Python version, dependency lock state, host class, and discovery setting.
