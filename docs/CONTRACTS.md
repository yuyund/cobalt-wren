# Contracts

This document fixes the boundaries between execution foundation, workflows, and services.

These contracts describe the current internal foundation surface. If parts of this surface become public later, they should do so through a facade, alias, or protocol rather than by exposing internal modules directly.

## Node Contract

- node は state patch dict を返す
- node は Django ORM を直接触らない
- node は concrete provider を import しない
- node は concrete tool を import しない
- node は raw input_payload を state に入れない
- node は raw LLM response / raw ToolResult.output を state に入れない

## Runner Contract

- runner は `ExecutionResult` を返す
- `ExecutionResult.output_payload` は service 層へ渡す output candidate
- runner は Run model を直接更新しない
- runner は safe persistence の責務を持たない

## Service Contract

- service 層が Run lifecycle を管理する
- service 層が `safe_run_output_payload()` で `Run.output_payload` を正規化する
- service 層が `safe_run_error_message()` で `Run.error_message` を正規化する

## Run.output_payload Contract

- `Run.output_payload` は UI/API に出せる safe summary
- raw prompt / raw response / raw tool output / secrets を含めない
- provider raw object を含めない
- traceback を含めない

## GraphExecutionInput Contract

- raw `Run.input_payload` の transient boundary
- `GraphRuntime.execution_input` として渡す
- checkpointable state には入れない
- state には `input_summary` のみ入れる

## GraphRuntimeConfig Contract

- execution-plane config は graph-local
- secret や raw input を入れない
- API key / base URL / provider raw object を入れない
- workflow config を runtime 用の安全な最小面へ変換する

`GraphRuntime` is currently a public candidate but still provisional. `GraphDefinition` is also internal foundation vocabulary for now; a future public facade may expose `WorkflowDefinition` as an alias or wrapper.

## Tool Contract

- tool result は安全な summary を返す
- raw tool output は state / output / EventSink に戻さない
- policy deny は observable だが、raw secret を含めない

## LLM Contract

- LLM result は raw object をそのまま state に流さない
- provider raw object は永続化しない
- model / token count / bounded summary は許可される
- secrets を messages に混ぜても永続化しない

## EventSink Contract

- EventSink は observability boundary
- EventSink payload は redaction-safe である
- EventSink failure は primary failure を上書きしない

## ArtifactStore Contract

- artifact store は metadata と body を分離する
- body は将来の永続化設計まで bounded に扱う
- raw secrets / raw provider payload を保存しない

## CheckpointStore Contract

- checkpoint state は safe summary / metadata のみ
- raw input / raw response / raw output を保存しない
- true resume は別途 contract が固まるまで未実装

## P0-B Public Facade Contract

- `langgraph_automation.api.llm`
- `langgraph_automation.api.tools`
- `langgraph_automation.api.stores`
- `langgraph_automation.api.events`

These modules re-export selected foundation interfaces. They do not expose workflow definition, runtime concrete implementation, plugin loader, config loader, or public error taxonomy yet.

## OutputCandidate / NodeResult

現時点の判断:

- OutputCandidate dataclass: まだ導入しない
- NodeResult dataclass: まだ導入しない

現時点では:

- node return = state patch dict
- `ExecutionResult.output_payload` = output candidate dict
