# Configuration Taxonomy

This document defines the configuration taxonomy for `langgraph-automation`.

The goal is to make clear:

- what can be changed through config
- what must stay in plugin code
- what the foundation guarantees for safety, policy, and observability
- how config stays independent from internal implementation details
- how future config loader / schema / plugin registration phases should be shaped

## Purpose

Configuration is the declarative control surface for package, deployment, workflow, plugin, provider, policy, observability, store, worker, and UI behavior.

Configuration is not for:

- executing arbitrary Python code
- fully describing workflow logic
- turning graphs or nodes into a DSL
- disabling safety boundaries
- swapping internal implementation details arbitrarily
- storing secret values in clear text

## Responsibility boundaries

### Config

Config may express:

- workflow enable / disable
- provider selection
- model selection
- limits
- tool allowlist
- observability level
- store backend
- UI visibility
- plugin-specific parameters

### Plugin code

Plugin code owns:

- graph structure
- nodes
- routing
- prompt assembly
- state schema
- domain policy
- business logic
- validation logic
- custom output mapping

### Foundation

Foundation guarantees:

- Run lifecycle
- GraphRuntime
- ToolPolicy enforcement
- safety redaction
- result safety
- observability failure masking
- config loading / validation framework
- plugin registration mechanism

The rule of thumb is:

- workflow structure lives in plugin code
- workflow behavior parameters live in config
- execution, safety, observability, and policy enforcement live in foundation

## Config taxonomy

### 1. Deployment config

Purpose:

- describe deployment environment and runtime defaults

Permitted:

- environment name
- timezone
- runtime mode
- debug display level

Forbidden:

- secret values
- arbitrary Python import
- internal module paths

Future implementation note:

- likely sourced from environment variables, Django settings, or deployment descriptors

Example:

```yaml
deployment:
  environment: development
  timezone: Asia/Tokyo
```

### 2. Runtime config

Purpose:

- choose the high-level execution mode and default workflow selection

Permitted:

- runtime mode
- default workflow kind
- high-level runtime defaults

Forbidden:

- internal class paths
- arbitrary runtime factory import
- safety boundary bypass

Future implementation note:

- runtime config should normalize deployment defaults and workflow defaults before assembly

Example:

```yaml
runtime:
  mode: django
  default_workflow: llm_echo_summary
```

### 3. Provider config

Purpose:

- define provider identity and provider defaults without embedding secrets

Permitted:

- provider name
- model name
- env var reference
- timeout
- retry
- temperature / max_tokens defaults

Forbidden:

- api_key values
- secret-bearing base_url values
- provider raw object persistence
- arbitrary client class import

Future implementation note:

- config names a provider; plugin / provider registry resolves it to an implementation; runtime assembly creates the concrete client

Example:

```yaml
providers:
  llm:
    default:
      provider: litellm
      model: gpt-4.1-mini
      base_url_env: LLM_BASE_URL
      api_key_env: LLM_API_KEY
```

### 4. Workflow config

Purpose:

- control per-workflow enablement and behavior parameters

Permitted:

- enabled / disabled
- workflow kind
- LLM profile
- tool allowlist
- limits
- workflow-specific config parameters

Forbidden:

- fully describing graph structure in YAML
- node Python paths
- arbitrary callable paths
- internal class imports
- raw prompt persistence toggles

Future implementation note:

- workflow config should be validated against registered workflow requirements before runtime assembly

Example:

```yaml
workflows:
  llm_echo_summary:
    enabled: true
    kind: llm_echo_summary
    llm_profile: default
    tools:
      allowed:
        - echo
    limits:
      max_steps: 5
```

### 5. Plugin config

Purpose:

- carry plugin-specific parameters once a plugin is explicitly registered

Permitted:

- plugin name
- plugin-specific config
- future plugin version constraints

Forbidden:

- arbitrary Python module paths
- arbitrary class paths
- pip install via config
- plugin discovery bypass

Future implementation note:

- Package MVP should use explicit / manual registration
- Package Complete may consider Python entry points or other discovery mechanisms

Example:

```yaml
plugins:
  enabled:
    - company_agent
    - github_tools
  config:
    company_agent:
      departments:
        - management
        - architecture
        - implementation
```

### 6. Tool policy config

Purpose:

- define which tools a workflow may use

Permitted:

- workflow allowlist
- denylist
- capability classification such as read/write/admin
- environment-specific restrictions

Forbidden:

- `allow_all: true`
- implicit shell/file/network permission
- policy bypass

Future implementation note:

- default deny should remain the baseline, with explicit allowlists per workflow

Example:

```yaml
policies:
  tools:
    default: deny
    workflows:
      llm_echo_summary:
        allow:
          - echo
```

### 7. Limits config

Purpose:

- bound execution cost and output size

Permitted:

- max_steps
- max_llm_calls
- max_tool_calls
- timeout
- output size
- metadata size

Forbidden:

- easy unlimited mode
- complete safety limit disablement

Future implementation note:

- limits should apply consistently across workflow, runtime, and provider boundaries

Example:

```yaml
limits:
  default:
    max_steps: 30
    max_llm_calls: 10
    max_tool_calls: 20
    max_output_chars: 10000
    timeout_seconds: 300
```

### 8. Observability config

Purpose:

- control observability capture level without exposing unsafe raw payloads

Permitted:

- summary capture on / off
- span level
- metadata limit
- backend selection

Forbidden:

- `full_prompt: true` by default
- `full_response: true` by default
- `raw_tool_output: true`
- `redaction: false`

Future implementation note:

- summary capture and bounded metadata should remain available, while secret redaction stays mandatory

Example:

```yaml
observability:
  capture:
    input_summary: true
    output_summary: true
    full_prompt: false
    full_response: false
    raw_tool_output: false
  metadata_limit_bytes: 4096
```

### 9. Store config

Purpose:

- choose artifact and checkpoint backends safely

Permitted:

- backend name
- env var reference
- retention
- max size

Forbidden:

- absolute path exposure in UI/API
- unsafe checkpoint body dumps
- secret values

Future implementation note:

- memory stores may remain for tests and local development; persistent stores will need explicit safety rules

Example:

```yaml
stores:
  artifact:
    backend: memory
  checkpoint:
    backend: memory
```

Future example:

```yaml
stores:
  artifact:
    backend: local_file
    root_env: ARTIFACT_ROOT
```

### 10. Worker config

Purpose:

- describe background execution topology without embedding workflow logic

Permitted:

- worker backend
- queue names
- concurrency

Forbidden:

- worker-specific business logic
- hidden process execution rules
- unsafe queue bypass

Future implementation note:

- worker backend is a future plugin concern; P1-A only records the taxonomy

Example:

```yaml
worker:
  backend: local
  queues:
    default:
      concurrency: 1
```

### 11. UI config

Purpose:

- control presentation and allowed actions

Permitted:

- visible
- label
- action availability
- display metadata

Forbidden:

- permission bypass
- hidden-field exposure
- raw payload display

Future implementation note:

- UI config must remain presentation-only; policy still owns authorization

Example:

```yaml
ui:
  workflows:
    llm_echo_summary:
      visible: true
      label: LLM Echo Summary
      actions:
        start: true
        retry: true
        resume: false
```

### 12. Safety config

Purpose:

- describe safety posture without allowing safety to be disabled

Permitted:

- mode: strict

Forbidden:

- `safety.enabled: false`
- `redaction.enabled: false`

Future implementation note:

- debug modes may tune logging verbosity, but they must not turn off secret redaction

Example:

```yaml
safety:
  mode: strict
```

## What config must never allow

Configuration must never permit:

- arbitrary Python import
- arbitrary callable path
- `safety.enabled = false`
- `redaction.enabled = false`
- `allow_all_tools = true`
- secret values in config
- raw provider response persistence
- raw tool output persistence
- full traceback persistence
- absolute local path exposure
- checkpoint raw dump without schema/version

Bad example:

```yaml
workflows:
  custom:
    builder: my_package.my_module.build_graph
```

Replacement principle:

```yaml
workflows:
  custom:
    kind: company_agent
```

The workflow kind is resolved by plugin registration, not by importing an arbitrary path from config.

## Config source and normalized config

Future config sources may include:

- `config.yaml`
- `pyproject.toml`
- Django settings
- environment variables
- database-stored `Workflow.definition_payload`

Important rule:

- multiple sources may exist, but runtime assembly must consume normalized config

Conceptual flow:

```text
raw config sources
  ↓
ConfigLoader
  ↓
ConfigNormalizer
  ↓
ValidatedPackageConfig
  ↓
RuntimeAssembly
```

P1-A defines the taxonomy only. It does not implement the loader, normalizer, schema, or parser.

## Relation to existing payloads

- Package-level config: deployment / provider / plugin / policy / store / observability defaults
- `Workflow.definition_payload`: database-backed workflow instance-specific config
- `Run.input_payload`: one execution input payload
- Normalized runtime config: package config + `Workflow.definition_payload` after validation and resolution

Do not mix these layers:

- package config and `Workflow.definition_payload` are not the same thing
- `Workflow.definition_payload` must not contain secret values
- `Run.input_payload` is not runtime config
- `Run.input_payload` must not be read for model / api_key / base_url / tools.allowed

## P1-A done when

- config taxonomy categories are written down.
- config / plugin code / foundation responsibilities are separated.
- package-level config / `Workflow.definition_payload` / `Run.input_payload` are distinct.
- arbitrary Python import is rejected.
- safety / redaction / policy bypass are rejected.
- config source and normalized config are described.
- loader / schema / parser remain unimplemented.
