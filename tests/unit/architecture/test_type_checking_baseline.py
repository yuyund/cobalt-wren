from __future__ import annotations

import json
from pathlib import Path


def test_mypy_baseline_has_explicit_debt_categories() -> None:
    root = Path(__file__).parents[3]
    baseline = json.loads((root / "config" / "mypy-baseline.json").read_text(encoding="utf-8"))
    assert set(baseline["categories"]) <= {
        "external_stub",
        "django_choice_typing",
        "internal_code",
    }
    assert baseline["total"] == sum(baseline["categories"].values())


def test_type_checking_policy_rejects_global_suppression() -> None:
    root = Path(__file__).parents[3]
    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
    assert "ignore_missing_imports = true" not in pyproject.lower()
    assert "follow_imports = \"skip\"" not in pyproject.lower()
