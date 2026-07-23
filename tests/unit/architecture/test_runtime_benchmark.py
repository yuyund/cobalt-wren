from __future__ import annotations

from scripts.benchmark_runtime import collect


def test_runtime_benchmark_has_stable_schema() -> None:
    result = collect(2)
    assert result["schema_version"] == 1
    operations = result["operations"]
    assert set(operations) == {"engine_create", "workflow_prepare", "workflow_execute"}
    for measurement in operations.values():
        assert measurement["iterations"] == 2
        assert 0 <= measurement["min_ns"] <= measurement["max_ns"]
