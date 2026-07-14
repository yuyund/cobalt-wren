# Codex Workflow

This document fixes the working protocol for Codex so task instructions can stay short and consistent.

## Standard Start Commands

Run these first when starting work:

```bash
git status --short --untracked-files=all
git ls-files --others --exclude-standard
git log -1 --oneline
git diff --stat
git diff --name-status
./venv/bin/python -V
./venv/bin/python -m pytest -q
./venv/bin/python -m ruff check .
./venv/bin/python manage.py check
```

## venv Rule

Always use the repository venv for checks:

```bash
./venv/bin/python -m pytest -q
./venv/bin/python -m ruff check .
./venv/bin/python manage.py check
```

Never use:

```bash
python -m pytest -q
python -m ruff check .
python manage.py check
```

## Git Rule

- Do not commit unless the user explicitly asks.
- Do not run `git add` unless the user explicitly asks.
- Do not omit `git status --short --untracked-files=all`.
- Always report untracked files.
- If generated or ignored files are touched, report why.

## Generated / Ignored Files

- `src/langgraph_automation.egg-info/` is generated metadata.
- If stale references appear there, note the finding in the report.
- Do not create or expand generated files unless they are needed to restore consistency.

## Stale egg-info Rule

- If `src/langgraph_automation.egg-info/SOURCES.txt` or related generated metadata references removed files, report it explicitly.
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
