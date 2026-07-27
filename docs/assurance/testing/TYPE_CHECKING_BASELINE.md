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
  - src/cobalt_wren/apps/automation/migrations/0001_initial.py
  - src/cobalt_wren/apps/automation/ui/builders.py
  - src/cobalt_wren/config/models.py
  - src/cobalt_wren/config/validator.py
  - src/cobalt_wren/integrations/llm/observed_client.py
  - src/cobalt_wren/integrations/tools/observed_registry.py
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

Full-source mypy runs against all package source with the Django plugin enabled.

- `django-stubs` and `django-stubs-ext` type the Django model, selector, URL, view, and migration boundaries.
- `django-environ` is the only targeted missing-stub override; the override applies only to the `environ` module.
- Package-owned source has no accepted mypy findings.

`config/mypy-baseline.json` is therefore a zero baseline. CI runs both `mypy src` and `scripts/classify_mypy.py --check-baseline`. Any new error fails immediately; the classifier remains as a diagnostic report if third-party typing changes introduce a new category.

Broad `ignore_missing_imports`, `follow_imports = "skip"`, and unreviewed `type: ignore` directives are prohibited.
