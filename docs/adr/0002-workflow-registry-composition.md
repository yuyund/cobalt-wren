# ADR 0002: Workflow registry composition boundary

## Status

Accepted

## Context

`graphs/registry.py` が concrete workflow definition を import すると、graphs が application workflow を知り始める。

## Decision

- `graphs/registry.py` は registry mechanism に寄せる。
- concrete workflow definitions は `workflows/catalog.py` 側で集約する。

## Consequences

- graphs は execution foundation として保たれる。
- workflow 追加時の変更点は `workflows/*` と catalog に閉じやすくなる。
