# Operating Protocol

This file captures the stable working rules for Codex on this repository.

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

