# Project State, Philosophy, and Complete Plan

## この文書の位置づけ

この文書は、現在の `cobalt-wren` プロジェクトについて把握している実装状態、設計判断、未完了事項、既知の矛盾、今後の計画を、一つの連続した説明としてまとめたものである。

個別の契約は `docs/contracts/core/CONTRACTS.md`、Native Authoring の詳細は `docs/workflows/authoring/NATIVE_AUTHORING_USE_CASE_DESIGN.md`、OSS integration の方向は `docs/architecture/design/OSS_NEUTRAL_WORKFLOW_INTEGRATION.md`、工程単位の進捗は `docs/roadmap/milestones/ROADMAP.md` が引き続き正本である。この文書はそれらを横断し、なぜこの構造を選んでいるのか、現状どこまで到達し、次に何を行うのかを説明する上位の文章である。

現在の作業は `main` branch 上の大きな未コミット差分として存在する。既存の変更には、今回の対話以前から存在する関連変更と無関係な変更が混在しているため、差分全体を一括して整理、破棄、commit してはならない。現時点で commit は行われていない。

---

## 1. プロジェクトが作ろうとしているもの

このプロジェクトは、LangGraph 専用の実行環境でも、特定企業の業務 workflow 集でもない。目的は、異なる workflow 実装を同じ運用基盤へ接続し、安全に実行、観測、保存、操作、表示できる workflow automation package と control plane を構築することである。

基盤が提供する中心価値は二つある。

第一に、workflow engine や実装方式が異なっても、Run lifecycle、監査、権限、失敗、安全な出力、artifact、checkpoint reference、操作、検索、UI を共通の運用面で扱えることである。

第二に、その共通運用面を作るために、各 workflow engine の情報を最小公倍数へ潰さないことである。基盤は framework 名を理解しないが、integration helper が public API から抽出した詳細を versioned projection として保持し、共通 UI の中へ安全に合成する。

したがって、このプロジェクトの方向は次の一文で表せる。

> workflow 実装の自由を保ちながら、運用、安全、監査、永続化、UI の境界を package-owned contract に収束させる。

---

## 2. これまでの判断から読み取れる利用者の思想

これまでの指示と判断から、プロジェクトに対する思想は次のように整理できる。

### 2.1 利用者は簡単に workflow を作れるべきである

workflow を作るために、最初から graph theory、checkpoint runtime、Django control plane、plugin registry、runtime assembly を理解させるべきではない。通常の Python 関数、`if`、`for`、戻り値、型注釈を保ち、運用上意味のある箇所だけを step として明示する体験を標準にする。

この思想が Native Authoring の出発点である。

### 2.2 簡単さのために基盤境界を壊してはならない

Native が foundation distribution に同梱されていても、基盤から特権的に扱ってはならない。組み込みだから専用 execution path、専用 persistence、専用 UI、integration ID branch を持つことは許されない。

Native、LangGraph、LlamaIndex Workflows、plain executable、外部 plugin は、authoring model や capability は異なっても、基盤へ入った後は同じ public contribution、opaque executable、execution context、result、EventSink、projection、Run lifecycle を通る。

### 2.3 組み込み例を製品機能に見せてはならない

単なる example を built-in catalog に登録すると、workflow kind の安定性、後方互換性、production support を暗黙に約束することになる。そのため `reference.llm_echo_summary` は削除され、foundation の built-in workflow catalog は空になった。

例は `examples/native/` に置き、明示的に登録した場合だけ動く。例は教材であり、製品 workflow ではない。

### 2.4 framework neutrality は情報損失ではない

中立性を理由に、全 engine を `started / succeeded / failed` の三状態だけへ落とすべきではない。基盤は framework branch を持たず、integration helper が public hook から task、step、event、interrupt、checkpoint reference、action descriptor を安全な projection として提供する。

### 2.5 基盤が持つべきものは技術機構ではなく安定した意味論である

外部 library は implementation であり architecture ではない。package が所有すべきなのは、safe output、error taxonomy、tool policy、artifact identity、workflow contribution、projection semantics、action validation、retention、UI specification などの意味論である。

一方、blob transport、database engine、framework runtime などは replacement boundary の後ろへ置く。

### 2.6 抽象化は数ではなく変更局所化で評価する

interface や facade が多いだけでは疎結合ではない。外部 workflow wheel を foundation 改修なしで追加できること、store や provider を交換できること、framework をインストールせず foundation を import できること、UI renderer が Django model や framework を知らないことが証拠になる。

### 2.7 安全性は adapter ごとの任意機能ではない

provider、tool、store、framework、renderer を交換しても、secret redaction、raw payload restriction、safe error、primary failure preservation、artifact body separation を迂回できてはならない。

---

## 3. 現在の architecture

現在の責務は概ね次の層へ分かれている。

```text
Public API / Authoring
├── api.engine
├── api.workflow
├── api.plugins
├── api.integrations
├── api.llm / api.tools / api.stores / api.events / api.errors
└── native

Preparation and Runtime
├── plugin registry
├── config loading / normalization / validation
├── runtime assembly
├── workflow preparation
└── generic capability adapter

Integrations
├── Native provider
├── LangGraph provider
├── LlamaIndex Workflows provider
├── LLM / tool observability decorators
├── artifact / checkpoint stores
└── Django EventSink

Control Plane
├── Run lifecycle
├── inline / worker execution
├── safe output and error persistence
├── spans / events / diagnostics
├── integration projections
├── common integration actions
└── audit

Presentation
├── renderer-neutral UI specs
├── semantic detail projections
├── integration summary / current state / timeline
├── live Run fragments and SSE
└── Django / Tabler renderer
```

重要なのは dependency direction である。workflow implementation から Django model、control-plane service、runtime registry へ依存してはならない。renderer は framework object や Django `_meta` を直接解釈しない。foundation execution path は integration ID を条件分岐に使用しない。

---

## 4. public workflow execution contract

workflow は最終的に `WorkflowContribution` を通じて登録される。contribution は workflow kind、metadata、requirements、input/output schema、build function を保持する宣言であり、registry 自身は workflow を実行しない。

準備後の実行経路は次の通りである。

```text
WorkflowContribution
→ WorkflowDefinition
→ build(WorkflowBuildContext)
→ opaque executable
→ generic adapter
→ execute / invoke / callable / optional resume
→ WorkflowExecutionResult
```

Django control plane からは次の一経路となる。

```text
Run
→ WorkflowReference
→ DeploymentEngineOwner
→ EnginePreparedWorkflow
→ opaque executable
→ WorkflowExecutionResult
→ ControlPlaneExecutionResult
→ safe Run persistence
```

workflow kind が未登録、definition payload が不正、requirements が不足、build が失敗した場合は fail closed である。旧 graph fallback は存在しない。

plain Python executable は低水準 SPI として維持されている。Native や外部 OSS integration を使わず、`execute(input_payload, context)` を持つ object を generic adapter が直接扱える。この経路は Native の代替となる主力 UX ではなく、独自 runtime や既存 system を接続する escape hatch である。

---

## 5. configuration と runtime assembly

設定は次の段階へ分離されている。

```text
source loading
→ structural parsing
→ normalization
→ semantic validation
→ plugin resolution
→ secret resolution
→ runtime construction
```

package config、database-backed `Workflow.definition_payload`、一回の実行入力である `Run.input_payload` は別物である。Run input から provider model、API key、base URL、tool allowlist、store backend を上書きしてはならない。

provider、tool、artifact store、checkpoint store、event sink は deployment configuration と runtime assembly が解決する。workflow は `WorkflowRequirements` で必要能力を宣言し、`WorkflowBuildContext` から名前によって受け取る。secret value は build context や runtime metadata へ混入しない。

`api.engine.create_engine(...)` が application-facing facade であり、PluginRegistry、ConfigValidator、RuntimeAssembler、WorkflowPreparer を隠す。control-plane preparation service もこの facade path へ寄せられている。

---

## 6. safety と failure semantics

安全性は全層に共通する contract である。

### 6.1 Run output

`Run.output_payload` は UI/API に表示可能な safe summary だけを保存する。raw prompt、raw provider response、raw tool output、secret、traceback、provider object は保存しない。

### 6.2 error

user-facing error は fixed safe message、code、category、bounded metadata だけを持つ。cause、traceback、diagnostic detail は user-facing dictionary に入らない。

### 6.3 observability

EventSink metadata と payload は bounded、redacted、JSON-safe でなければならない。observability failure は secondary failure であり、primary execution result や primary exception を上書きしない。

### 6.4 retained diagnostics

必要な詳細は `DiagnosticPayload` として redaction、depth/item/byte limit、retention を適用して保存する。UI の inspect details は permission check と audit を通る。既に truncation marker へ置き換えられた過去データを復元可能であるかのように表示しない。

---

## 7. persistence

### 7.1 ArtifactStore

artifact body と control-plane metadata は分離される。body は store にあり、Django DB には name、kind、storage key、content type、size、digest、safe metadata だけを保存する。

実装済み backend は次の通りである。

- `MemoryArtifactStore`: EPHEMERAL default
- `FilesystemArtifactStore`: PROCESS_DURABLE explicit opt-in

immutable write、idempotent retry、conflict detection、digest/size integrity が contract である。

### 7.2 CheckpointStore

checkpoint は versioned、append-only、serializer-aware、conflict-aware な execution-state repository として設計されている。

実装済み backend は次の通りである。

- `MemoryCheckpointStore`: EPHEMERAL reference
- `FilesystemCheckpointStore`: PROCESS_DURABLE explicit opt-in

ただし store durability は true resume を意味しない。package CheckpointStore と LangGraph BaseCheckpointSaver、pending writes、thread identity、namespace、serializer、retry、time travel の収束設計は未完了である。

---

## 8. observability、projection、UI

control plane は canonical record と integration projection を併用する。

### 8.1 canonical records

Run、ExecutionSpan、RunEvent、Artifact、CheckpointMetadata、ExecutionJob、audit record などは共通運用に必要な indexed record である。

### 8.2 integration projections

framework-specific detail は `IntegrationProjectionRecord` へ append-only で保存される。各 record は integration ID、schema ID、owner、subject、projection kind、sequence、occurred_at、classification、retention、bounded payload を持つ。

projection kind は次の四つである。

- snapshot
- event
- reference
- action

snapshot は current state を更新し、event は timeline に加わり、reference と action は状態として誤表示されない。

### 8.3 UI composition

Run detail は次の三層を統合する。

- Integration Summary
- Current Integration State
- Integration Timeline
- Technical Projections

renderer は integration ID や schema ID を opaque な分類として扱い、LangGraph、LlamaIndex、Native 用の template branch を持たない。

### 8.4 live Run UI

Run UI は stable control-plane records だけを読み、ASGI では SSE、WSGI では HTMX polling fallback を使う。current activity、failure diagnostic、LLM conversation summary、node output、timeline が component registry から構成される。

raw prompts や raw responses は表示せず、bounded redacted previews と token/latency metadata を表示する。

---

## 9. integration foundation

`api.integrations` に framework-neutral vocabulary があり、central definition が integration identity、distribution、import name、provider path、version range、maturity、priority、capabilities、limitations、documentation、auto-detection eligibility を宣言する。

registry は availability inspection、version compatibility、lazy provider loading、definition consistency を管理する。explicit selection が安定経路であり、automatic inference は convenience layer として未実装である。

Integration Health UI は central definition と registry inspection から構成され、次の状態を区別する。

- ready
- not installed
- version incompatible
- load failed
- invalid
- definition mismatch

provider exception text、traceback、private path は UI に出さない。

---

## 10. LangGraph integration の現状

LangGraph は optional extra であり、base dependency ではない。provider は public stream API と `Command(resume=...)` を利用し、compiled graph private attribute を解析しない。

現在の主な projection は次の通りである。

- `langgraph.task.v1`
- `langgraph.interrupt.v1`
- `langgraph.checkpoint_ref.v1`

interrupt 時には common `integration.actions.v1` の Resume descriptor を生成できる。server は descriptor を execution authority として信用せず、Run state、projection ownership/expiry、action availability、current executable resume capability を再検証し、共通 `dispatch_resume` 経路へ渡す。

inline と worker resume は同じ normalized request を使用する。

LangGraph が担当する高度な領域は次である。

- checkpoint recovery
- durable pause/resume
- human/external input wait
- time travel / fork
- graph cycles
- stateful subgraphs
- agent memory

foundation は checkpoint body を複製せず、安全な reference と action route を保持する。

---

## 11. LlamaIndex Workflows integration の現状

LlamaIndex Workflows は optional extra であり、public `Workflow.run()`、`WorkflowHandler`、`stream_events(expose_internal=True)`、`StepStateChanged` を利用する。

現在の projection は次の通りである。

- `llamaindex.step.v1`
- `llamaindex.event.v1`

step は canonical span へ写像され、async execution 中の observability operation は buffer され、handler completion 後に synchronous EventSink へ replay される。

現在の capability depth は observable であり managed ではない。execute、step observability は対応し、event view は部分対応である。waiting、resume、checkpoint management、external event injection、common cancellation action は未対応である。

この integration により、共通 projection と UI が graph-centric な仕組みに限定されていないことを証明している。

---

## 12. external distribution proof

別 distribution の `oss-integration-workflows` wheel が LangGraph と LlamaIndex Workflows の workflow を entry point group `cobalt_wren.plugins` から提供する。

clean-room test は foundation と external package を wheel build し、新しい virtual environment へ install し、entry point discovery、SQLite migration、database-backed Workflow/Run resolution、execution、span/projection persistence、current state、timeline、summary、Run detail HTML rendering を確認する。

plain Python executable についても別 external package test があり、LangGraph dependency なしで wheel install と entry point discovery が成立することを確認している。

Native external wheel proof はまだ未実装である。

---

## 13. Native Authoring の思想

Native は reduced LangGraph ではない。普通の Python control flow を維持したまま、明示的な named step boundary に retry、timeout、cancellation、observability、artifact、progress、metric などを付与する標準 authoring experience である。

Native 自身も integration である。`NativeWorkflow` は authoring object であり、official Native provider が opaque executable へ変換する。generic preparer、adapter、engine facade、Django execution、persistence、UI は Native implementation を import せず、`integration_id == "native"` の分岐を持たない。

Native を使うべきなのは、秒から数十分程度で一 Run 内に完了し、普通の business logic、API、LLM、tool、bounded loop、artifact が中心であり、process failure 後に workflow 全体を再実行できる場合である。

LangGraph を使うべきなのは、任意 step からの recovery、長時間 wait、human approval、graph cycle、time travel、stateful subgraph、durable agent memory が必要な場合である。

---

## 14. Native の実装済み範囲

### 14.1 P1 foundation

実装済み public surface は次の通りである。

- `workflow(...)`
- `NativeWorkflow`
- `NativeWorkflowContext`
- `NativeExecutable`
- `.contribution(...)`
- `.plugin(...)`

workflow decorator は AST を解析せず、control flow を書き換えず、local variable を serialize しない。

workflow execution は async-first であり、step は sync/async callable を受け取る。sync callable は `asyncio.to_thread()` で実行する。直接の synchronous execute を active event loop 内から呼ぶことは明示的に拒否する。

Django EventSink は synchronous であるため、Native は async 実行中に symbolic lifecycle を buffer し、workflow completion/failure 後に synchronous context で span と projection を replay する。

各 step は canonical `step` span と `native.step.v1` snapshot を生成する。failure は元例外を primary execution boundary へ再送出するが、永続化する error message は固定された安全な文言である。

### 14.2 P2A policy core

実装済みである。

- `RetryPolicy`
- attempt ごとの canonical span
- `running / retrying / succeeded / failed` snapshot
- per-step `timeout_seconds`
- workflow deadline との min timeout
- retry delay 中の cancellation check
- `occurrence_key`
- duplicate occurrence rejection
- safe occurrence key format
- Run あたり最大 1,000 step occurrence

async callable は timeout boundary で cancel される。sync callable は await 側が timeout しても underlying thread を強制終了できないため、library 自身の timeout が必要である。

retry は idempotency を保証しない。side effect の重複防止は application 側の idempotency key などで担保する。

### 14.3 control-plane proof

Native workflow は通常の Plugin として engine へ明示登録され、Django Run、safe output、step span、projection、current state、timeline、generic UI を通る。

retry attempt persistence と terminal timeout が Run の `timed_out` へ正規化される縦断テストがある。

---

## 15. built-in workflow と examples

foundation は現在 product workflow を一つも同梱しない。built-in catalog は意図的に空である。

旧 `reference.llm_echo_summary` package、専用 executable、state、関連 test は削除された。旧 workflow kind や import が source、tests、docs に残らないことを監査した。

Native の利用例は次に分離された。

```text
examples/native/
├── sequential_pipeline.py
├── conditional_routing.py
├── retrying_api.py
└── bounded_loop.py
```

これらは implicit registration されず、stable product workflow kind や compatibility promise を作らない。application が Plugin を明示登録するか、外部 distribution が entry point で公開する。

engine と control-plane の test は hidden built-in workflow に依存せず、`tests/support/native_workflow_fixtures.py` の explicit test Plugin を使用する。

---

## 16. Native で現在できるユースケース

現在、正式に成立している中心領域は、単一 Run 内で完了する bounded business workflow である。

対応済み:

- sequential pipeline
- ordinary Python conditional routing
- bounded loop
- stable occurrence identity
- sync and async step
- external API call
- explicit retry/backoff
- step timeout
- workflow deadline
- cooperative cancellation
- provider lookup
- tool lookup
- artifact store lookup
- failure observability
- attempt history
- common current state and timeline
- Plugin / Contribution conversion
- inline / worker control-plane execution

基礎能力のみ:

- LLM: provider は取得できるが Native convenience API はない
- tool: tool は取得できるが observed call convenience API はない
- artifact: store は取得できるが write convenience API はない

未実装:

- artifact convenience API
- automatic artifact reference emission
- progress projection API
- metric projection API
- reusable configured step definition
- recipe layer
- bounded concurrency
- subworkflow semantics
- partial collection failure policy
- caching
- idempotency metadata
- compensation hook
- Native external wheel proof

明示的な非目標または高度 integration の領域:

- arbitrary checkpoint continuation
- durable waiting
- multi-day timer
- human approval resume
- deterministic replay of arbitrary Python
- time travel / state fork
- exactly-once side effects
- arbitrary distributed fan-out
- event sourcing
- dynamic DAG persistence
- stateful agent loops
- transparent recovery from process death during a callable

---

## 17. 次に実装する 1 から 6

利用者は次の六項目を順に進める判断をしている。

### 17.1 Artifact convenience API

目標は、workflow author が raw ArtifactStore contract と storage key construction を毎回扱わず、次のように書けることである。

```python
artifact = await ctx.artifact.write(
    name="report.json",
    content=result,
    kind="report",
    content_type="application/json",
    metadata={"classification": "internal"},
)
```

必要な意味論:

- execution-owned run identity
- deterministic or explicitly supplied safe storage key
- bytes / text / JSON convenience serialization
- `ArtifactWriteRequest` への変換
- store-derived size/digest
- `artifact_created` EventSink emission
- Run/step association
- safe `NativeArtifact` descriptor
- body を output/projection/DB metadata へ複製しない
- store failure を primary artifact step failure として扱う

この API は新しい persistence path を作らず、既存 ArtifactStore と EventSink へ委譲する。

### 17.2 Progress and metric projections

期待 API:

```python
ctx.progress(completed=30, total=100, message="Processing documents")
ctx.metric("documents_processed", 30, unit="count")
```

初期 schema:

- `native.progress.v1`: stable workflow-level snapshot
- `native.metric.v1`: append-only event

必要な制約:

- numeric validation
- total > 0
- completed range validation
- bounded message
- bounded dimensions
- deterministic sequence
- safe retention/classification
- generic Current State / Timeline / Technical Projection UI で表示
- Native-specific renderer branch を追加しない

progress の aggregation、nested workflow scope、parallel progress は初期版では扱わない。

### 17.3 LLM and tool convenience API

目標は provider/tool plumbing と observability decoration を workflow author から隠すことである。

期待 API:

```python
result = await ctx.llm.complete(
    "summarize",
    messages,
    profile="default",
    retry=RetryPolicy(max_attempts=3),
    timeout_seconds=20,
)

result = await ctx.tool.run(
    "search",
    "web-search",
    query=query,
)
```

既存 `ObservedLLMClient` と `ObservedToolRegistry` を使用し、Native step span の内側に LLM/tool span を作る。raw provider/tool object を output や projection に保存しない。

初期版では streaming、structured output validation、tool policy DSL は扱わず、既存 public contracts の thin convenience とする。

### 17.4 Reusable configured step definitions

期待 API:

```python
fetch_customer = step(
    "fetch-customer",
    fetch_customer_record,
    retry=RetryPolicy(max_attempts=3),
    timeout_seconds=20,
)

customer = await ctx.run(fetch_customer, customer_id)
```

`StepDefinition` は immutable metadata object であり、execution state や context を保持しない。同じ definition を複数 workflow で再利用できる。

per-call occurrence key や必要に応じた policy override の範囲は contract test で固定する。decorator magic や AST inference は導入しない。

### 17.5 External Native wheel proof

別 distribution を追加し、Native workflow が foundation source tree 外から次を満たすことを証明する。

- public `cobalt_wren.native` と `api.*` だけを import
- `cobalt_wren.plugins` entry point で discovery
- foundation と plugin の wheel build/install
- fresh virtual environment
- isolated SQLite migration
- database-backed Workflow/Run
- Native provider resolution
- execution
- step span
- native projections
- artifact/progress/metric が実装済みならその persistence
- common UI rendering
- foundation framework branch なし

この証明が完了するまで、Native の外部配布性は API 上可能でも distribution-level complete とは主張しない。

### 17.6 Recipe layer

Level 1 の最小 recipe として、まず sequential workflow を提供する。

```python
workflow = sequential_workflow(
    name="document-review",
    steps=(extract, classify, summarize),
)
```

recipe は Level 2 Native workflow と StepDefinition へ compile し、別 execution semantics を持たない。

初期 recipe の制約:

- 一つ前の step result を次へ渡す
- 最初の step は input mapping を受け取る
- empty step list を拒否
- ordinary contribution/plugin conversion を使用
- recipe-specific control-plane branch を作らない

条件分岐 recipe、fan-out recipe、approval recipe は Level 2 API の安定後に別判断する。

---

## 18. 1 から 6 の実行順序

推奨順序は次の通りである。

1. artifact helper の public type と vertical test
2. progress/metric projection と generic UI test
3. LLM/tool convenience と nested span test
4. reusable StepDefinition と recipe の基礎
5. external Native distribution package
6. clean-room Django/UI proof
7. examples と author guide 更新
8. central integration capability/limitation 更新
9. contract/roadmap 同期
10. related regression、ruff、mypy、Django check、migration check

外部 wheel proof は convenience API の形が定まってから行う。そうしないと provisional API を external distribution test が早期に固定するためである。

---

## 19. 1 から 6 の後に検討するもの

次段階候補:

- bounded concurrency
- subworkflow identity and parent span semantics
- partial collection failure
- result caching
- idempotency key metadata
- compensation hooks
- richer LLM structured result helper
- tool policy convenience
- artifact classification/retention convenience
- progress scope and aggregation
- application scaffold generation for Native
- conformance suite for external Native packages

別設計 block が必要なもの:

- human approval
- durable waiting
- webhook/event resume
- true checkpoint recovery
- package CheckpointStore と LangGraph saver の convergence
- execution outbox / queue durability
- distributed fan-out
- Saga semantics

これらは Native convenience の延長として暗黙に実装せず、managed execution contract として再設計する。

---

## 20. 現在把握している文書上の不整合

worktree は大きな開発途中であり、一部文書には過去状態の表現が残っている。

特に `OSS_NEUTRAL_WORKFLOW_INTEGRATION.md` と `ROADMAP.md` の一部には、削除済み reference workflow や過去の built-in reference 方針を前提とする文章が残る可能性がある。一方、README、Native design、contracts の末尾では built-in catalog が空で examples が非登録であることを明記している。

今後の docs reconciliation では次を正本に統一する。

- foundation は product workflow を同梱しない
- built-in workflow catalog は空
- Native examples は `examples/native/`
- plain executable は独立 SPI
- LangGraph/LlamaIndex/Native は integration registry 上の capability producer
- reference workflow は存在しない

また `CONTRACTS.md` には歴史的な重複 section や旧 control-plane adapter 表現が残っているため、契約を削らずに内容を統合する cleanup block が必要である。

---

## 21. 検証状態

直近で確認済みの主な結果:

- built-in workflow 削除後の関連回帰: 85 passed
- Native P2A、integration、Django、docs 関連回帰: 51 passed
- Native reference 移行時点の関連回帰: 49 passed。その後 reference 自体を削除
- Ruff: 関連対象で成功
- Mypy: Native と関連対象で成功
- Django system check: 問題なし
- `makemigrations automation --check --dry-run`: 差分なし
- `git diff --check`: 成功
- empty built-in catalog runtime verification: 成功
- external plain Python wheel test: 成功
- external OSS integration clean-room test:既存実装あり

ただし repository 全 test suite は実行していない。worktree は大きく dirty であり、commit もない。したがって、現状は機能 block ごとの強い関連証拠はあるが、一つの release candidate として統合済みとはまだ言えない。

---

## 22. commit と変更管理

現時点では commit しない。理由は、user の明示指示がなく、worktree に多数の既存変更が混在しているためである。

今後 commit を行う場合は、最低でも次の論理単位へ分割する必要がある。

- integration contracts and registry
- projection persistence and UI
- integration actions
- LangGraph provider
- LlamaIndex provider
- optional dependency and external wheel proof
- Native P1
- Native P2A
- built-in catalog/reference removal and examples
- Native P2B convenience APIs
- docs reconciliation

ただし既存差分が既に混ざっているため、実際の分割には慎重な file-level review が必要である。

---

## 23. 最終的に目指す利用者体験

初心者または通常の application author は、次の程度のコードで workflow を作る。

```python
@workflow(name="document-report")
async def document_report(ctx, request):
    ctx.progress(completed=0, total=3, message="Starting")

    extracted = await ctx.step("extract", extract, request["document"])
    ctx.progress(completed=1, total=3, message="Extracted")

    summary = await ctx.llm.complete(
        "summarize",
        [{"role": "user", "content": extracted}],
        timeout_seconds=20,
    )
    ctx.progress(completed=2, total=3, message="Summarized")

    artifact = await ctx.artifact.write(
        name="summary.json",
        content={"summary": summary.content},
        kind="report",
    )

    ctx.metric("reports_created", 1, unit="count")
    ctx.progress(completed=3, total=3, message="Complete")

    return {
        "summary": summary.content,
        "artifact": artifact,
    }
```

この workflow は普通の Plugin へ変換され、application が明示登録する。

高度な workflow author は LangGraph または LlamaIndex Workflows を選び、同じ control plane へ接続する。独自 runtime author は plain executable SPI または integration provider を実装する。

基盤はどの方式で書かれたかを判断せず、同じ Run、safe persistence、audit、action routing、projection、UI を提供する。

---

## 24. プロジェクトの判断基準

今後の実装は常に次を満たす必要がある。

1. 利用者の workflow 作成を実際に簡単にするか。
2. foundation に framework-specific branch を追加していないか。
3. bundled implementation に特権を与えていないか。
4. public contract が implementation より小さく安定しているか。
5. raw payload、secret、traceback、provider object を露出しないか。
6. primary failure を secondary observability failure が上書きしないか。
7. external package から foundation 改修なしで利用できるか。
8. replacement または extension test があるか。
9. example を product contract と誤認させていないか。
10. durable semantics を実装していないのに resume や exactly-once を暗示していないか。

---

## 結論

現在のプロジェクトは、単なる workflow runner から、OSS-neutral integration、safe projection persistence、common actions、dynamic UI、Native Authoring を備えた control-plane foundation へ進んでいる。

基盤側の最重要境界は概ね成立している。LangGraph と LlamaIndex Workflows は異なる実行モデルでありながら同じ canonical records、projection、UI を通る。Native は bundled であっても同じ integration boundary を通り、plain executable は独立した低水準 SPI として残る。foundation は product workflow を同梱せず、examples と test fixtures を明示登録へ分離した。

Native は現在、普通の Python workflow runtime として sequential flow、branch、bounded loop、retry、timeout、cancellation、step observability、Plugin conversion まで到達している。一方、利用者にとって本当に簡単な product experience にするには、artifact、progress、metric、LLM/tool convenience、reusable step、external wheel proof、recipe layer が必要である。

次の主要作業は、この六項目を既存 contract の上へ追加し、Native にだけ許された private path を一切作らず、外部 wheel と Django control plane の縦断証拠まで完成させることである。
