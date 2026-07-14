# ADR 0003: Package / Plugin 方向性

## Status

Accepted

## Context

最終的には package 化し、application workflow / tool / provider / store を plugin として追加できるようにしたい。

## Decision

- package core は実行基盤・public API・config validation・plugin registration を担当する。
- application workflow は plugin として追加する。
- workflow structure は Python plugin、挙動パラメータは config に寄せる。
- safety redaction は config で無効化させない。

## Consequences

- public/internal API surface design を Package P0 として早めに行う。
- config taxonomy と plugin taxonomy を先に決める。
