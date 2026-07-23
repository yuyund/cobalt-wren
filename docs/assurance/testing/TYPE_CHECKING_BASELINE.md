---
type: audit
status: current
authority: normative
summary: Full-source mypy debt classification and non-regression policy.
code_refs:
  - scripts/classify_mypy.py
  - config/mypy-baseline.json
  - pyproject.toml
  - .github/workflows/ci.yml
test_refs:
  - tests/unit/architecture/test_type_checking_baseline.py
verified:
  date: 2026-07-23
  commit: WORKTREE
  base_commit: 1b3b7c7
  method:
    - full-mypy-classification
---
# Type Checking Baseline

Full-source mypy is executed against `src`. Existing findings are classified rather than globally suppressed.

- `external_stub`: third-party packages without installed typing metadata, primarily Django and django-environ.
- `django_choice_typing`: Django runtime choice constants represented as `(value, label)` tuples where application code expects the stored string value.
- `internal_code`: package-owned typing defects that must be reduced directly.

`config/mypy-baseline.json` records the current category counts, error codes, and affected files. CI runs `scripts/classify_mypy.py --check-baseline`; any category or total count increase fails. Reductions are accepted and require regenerating the baseline in the same reviewed change.

The baseline is not a waiver. New `type: ignore` directives or broad `ignore_missing_imports` settings are not permitted as substitutes for fixing package-owned errors.
