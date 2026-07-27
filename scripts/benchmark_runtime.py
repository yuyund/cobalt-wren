from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import median
from time import perf_counter_ns

from cobalt_wren.api.engine import create_engine
from tests.external_packages.acme_workflows.plugin import EXTERNAL_WORKFLOW_KIND, create_plugin


def _measure(operation, iterations: int) -> dict[str, float | int]:
    samples: list[int] = []
    for _ in range(iterations):
        start = perf_counter_ns()
        operation()
        samples.append(perf_counter_ns() - start)
    ordered = sorted(samples)
    p95_index = min(len(ordered) - 1, max(0, int(len(ordered) * 0.95) - 1))
    return {
        "iterations": iterations,
        "median_ns": int(median(ordered)),
        "p95_ns": ordered[p95_index],
        "min_ns": ordered[0],
        "max_ns": ordered[-1],
    }


def collect(iterations: int) -> dict[str, object]:
    config = {"version": 1, "environment": "benchmark"}
    plugin = create_plugin()
    engine = create_engine(config, plugins=(plugin,), discover_plugins=False)
    prepared = engine.prepare_workflow(EXTERNAL_WORKFLOW_KIND, config={"prefix": "bench"})
    return {
        "schema_version": 1,
        "operations": {
            "engine_create": _measure(
                lambda: create_engine(config, plugins=(plugin,), discover_plugins=False), iterations
            ),
            "workflow_prepare": _measure(
                lambda: engine.prepare_workflow(EXTERNAL_WORKFLOW_KIND, config={"prefix": "bench"}),
                iterations,
            ),
            "workflow_execute": _measure(
                lambda: prepared.execute({"request_id": "REQ-BENCH"}), iterations
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=25)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.iterations <= 0:
        raise SystemExit("iterations must be positive")
    result = collect(args.iterations)
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
