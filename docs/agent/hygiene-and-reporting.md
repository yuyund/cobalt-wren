# Hygiene and Reporting

This file keeps the non-code operational hygiene rules in one place.

## Generated / Ignored Files

- `../../src/langgraph_automation.egg-info/` is generated metadata.
- If stale references appear there, note the finding in the report.
- Do not create or expand generated files unless they are needed to restore consistency.

## Stale egg-info Rule

- If `../../src/langgraph_automation.egg-info/SOURCES.txt` or related generated metadata references removed files, report it explicitly.
- If the generated metadata is ignored, do not promote it into normal source control as part of routine work.

## Reporting Template

Use this shape in final reports:

```md
## 作業対象
- workspace path:
- git branch:
- HEAD:
- git status --short --untracked-files=all:
- git ls-files --others --exclude-standard:
- git diff --stat:
- git diff --name-status:
- ./venv/bin/python -V:

## 実施内容

## 変更ファイル

## 設計境界への影響

## tests / checks
- ./venv/bin/python -m pytest -q
- ./venv/bin/python -m ruff check .
- ./venv/bin/python manage.py check

## 未実装・TODO

## 残リスク
```

## Prohibitions

- Do not add commit history unless requested.
- Do not widen scope into feature design when the task is documentation-only.
- Do not bypass the venv command rules.
- Do not ignore generated-file hygiene.
- Do not hide untracked files.
