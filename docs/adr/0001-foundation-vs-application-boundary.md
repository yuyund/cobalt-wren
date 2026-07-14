# ADR 0001: Foundation と Application workflow の境界

## Status

Accepted

## Context

company_agent / planner / reviewer / executor のような application workflow を将来載せたい。

ただし、これを foundation に混ぜると基盤が application-specific になる。

## Decision

- foundation は application を知らない。
- application workflow は `workflows/applications` または plugin として載せる。
- `llm_echo_summary` は reference diagnostic workflow として扱う。

## Consequences

- application 実装はまだ行わない。
- foundation は workflow を登録・実行・観測・制御する能力に集中する。
