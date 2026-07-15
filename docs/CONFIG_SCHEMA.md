# Configuration Schema Boundaries

This document defines the configuration schema boundaries for `langgraph-automation`.

Purpose:

- separate raw config sources from the config that runtime sees
- separate schema validation, normalization, and resolution responsibilities
- fix source precedence before loader work starts
- fix secret / env var reference handling before runtime assembly exists
- require name-based resolution for provider / plugin / store / worker
- keep workflow-specific config out of the core schema
- `plugins.enabled` selects from manually registered plugins and does not trigger imports or discovery

## 3-layer config model

### RawPackageConfig

`RawPackageConfig` is source-facing config coming from YAML, TOML, Django settings, environment overrides, or DB-backed payloads.

Characteristics:

- many fields are optional
- defaults are not yet applied
- source-specific shorthand may still be present
- env var references may still be strings
- validation has not yet run
- secret values must not be stored

Example:

```yaml
version: 1
providers:
  llm:
    default:
      provider: litellm
      model: gpt-4.1-mini
      api_key_env: LLM_API_KEY
```

`RawPackageConfig` must not be consumed directly by runtime assembly.

### ValidatedPackageConfig

`ValidatedPackageConfig` is the merged, normalized, and validated package-level config.

Characteristics:

- defaults have been applied
- schema version is fixed
- unknown core fields have been rejected
- arbitrary imports have been rejected
- safety bypasses have been rejected
- secret values are not present
- provider / plugin / store / worker entries are name-based only
- `plugins.enabled` is a list of registered plugin names that become active for the config
- no concrete runtime objects are included

`ValidatedPackageConfig` holds names and validated parameters only. It does not hold provider, store, or plugin instances.

### ResolvedWorkflowConfig

`ResolvedWorkflowConfig` is the workflow-specific configuration obtained by combining `ValidatedPackageConfig` with `Workflow.definition_payload`.

Characteristics:

- workflow kind is fixed
- llm profile is fixed
- allowed tool names are fixed
- limits are fixed
- observability policy is fixed
- store / checkpoint backend profiles are fixed
- workflow-specific config remains after plugin validation
- secret values are not present
- no concrete dependency instances are present

`ResolvedWorkflowConfig` must not mix in `Run.input_payload`. `Run.input_payload` is execution input, not a config override.

## Runtime boundaries

### RuntimeAssembly

`RuntimeAssembly` is the boundary that converts resolved config into runtime dependencies.

It is responsible for building or wiring:

- concrete `LLMClient`
- concrete `ToolRegistry`
- concrete `ArtifactStore`
- concrete `CheckpointStore`
- concrete `EventSink`

### RuntimeDependencies

`RuntimeDependencies` is the set of concrete runtime objects produced by runtime assembly.

Examples:

- `LLMClient`
- `ToolRegistry`
- `ArtifactStore`
- `CheckpointStore`
- `EventSink`

### GraphRuntimeConfig

`GraphRuntimeConfig` is the safe graph-local config that a runtime bundle can carry during execution.

It must not include:

- `api_key`
- secret values
- provider raw objects
- concrete provider clients
- raw `Run.input_payload`
- raw `Workflow.definition_payload`
- raw config sources

## Source precedence

### Package-level config resolution

Precedence:

```text
built-in defaults
  < package config file
  < environment-specific override
  < Django settings
```

Later sources win, but only if they pass security validation.

### Workflow-level config resolution

Precedence:

```text
ValidatedPackageConfig workflow defaults
  < Workflow.definition_payload
```

`Workflow.definition_payload` is workflow-instance-specific config. It may refine validated defaults, but it must not introduce secret values, arbitrary imports, safety bypasses, or tool policy bypasses.

### Run execution input

`Run.input_payload` is not a config source.

It may be combined with `ResolvedWorkflowConfig` for execution, but it must not override:

- api key
- base URL
- provider
- model
- tools.allowed
- store backend
- checkpoint backend
- observability raw capture
- safety mode

## Versioning

- `version` is required
- unknown major versions are rejected
- minor-compatible extension is a future concern
- migration policy is deferred to Package Complete

## Unknown field policy

### Core config

- unknown top-level fields are rejected
- unknown core fields are rejected

### Plugin-specific config

- core treats plugin-specific mappings as opaque
- plugin-specific schemas validate those mappings
- unknown plugin-specific fields are decided by the plugin schema

This keeps typos visible while preserving extension flexibility.

## Secret and env var reference handling

Allowed:

```yaml
providers:
  llm:
    default:
      api_key_env: LLM_API_KEY
      base_url_env: LLM_BASE_URL
```

Forbidden:

```yaml
providers:
  llm:
    default:
      api_key: sk-...
      base_url: https://token@example.com
```

Rules:

- config may carry env var names
- config must not carry secret values
- env var resolution happens in runtime assembly
- validated / resolved config never stores secret values
- logs / errors / EventSink payloads must not reveal secrets

Validation rules for references:

- `*_env` values are validated as environment variable names
- secret-looking literals are rejected
- URLs containing credentials are rejected

## Name-based resolution boundary

Config must use names, not concrete class paths.

Bad example:

```yaml
providers:
  llm:
    default:
      class: langgraph_automation.integrations.llm.litellm_client.LiteLLMClient
```

Good example:

```yaml
providers:
  llm:
    default:
      provider: litellm
```

Similar examples:

```yaml
stores:
  artifact:
    backend: memory
observability:
  backend: none
worker:
  backend: local
```

Boundary:

- config schema carries provider / backend / plugin names
- registries resolve names to implementations
- runtime assembly instantiates concrete implementations

Arbitrary Python imports and arbitrary callable paths are forbidden.

## Workflow-specific config boundary

Recommended shape:

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
    config:
      summary_style: concise
```

Core schema knows:

- `enabled`
- `kind`
- `llm_profile`
- `tools`
- `limits`

Core schema treats as opaque:

- `workflows.<name>.config`

Plugin schemas validate workflow-specific config such as:

- `summary_style`
- `departments`
- `routing_policy`
- `output_format`
- application-specific settings

Core schema must not understand application-specific config semantics.

## Tool policy schema boundary

Recommended shape:

```yaml
policies:
  tools:
    default: deny
    workflows:
      llm_echo_summary:
        allow:
          - echo
```

Rules:

- default deny
- workflow-specific allowlist
- tool plugins remain unusable unless policy allows them
- allow_all is forbidden

Bad example:

```yaml
policies:
  tools:
    allow_all: true
```

## Validation layering

### Layer 1: raw schema validation

- type checking
- required fields
- version checking
- unknown fields
- top-level structure

### Layer 2: security validation

- secret values are forbidden
- arbitrary Python import is forbidden
- arbitrary callable path is forbidden
- safety bypass is forbidden
- redaction bypass is forbidden
- allow_all_tools is forbidden
- raw persistence is forbidden

### Layer 3: semantic validation

- provider profile exists
- workflow kind exists
- llm_profile exists
- tool allowlist references known tools
- limits are within bounds
- store backend profile exists
- observability backend profile exists

### Layer 4: plugin-specific validation

- workflow-specific config
- tool-specific config
- provider-specific config
- plugin-specific config

Plugin-specific validation must stay out of the core schema.
The plugin-specific validation rules for workflow, tool, provider, store, worker, and UI config are defined in `docs/PLUGINS.md`.
Plugin-specific validation hooks are defined conceptually in `docs/PLUGIN_API_SHAPE.md`.
Config validation invokes those hooks after raw schema, security, and semantic validation.
Configuration and plugin-specific validation failures are categorized in `docs/ERROR_TAXONOMY.md`.
Config validation errors must not expose raw config, secret-like literals, env var values, or full tracebacks.

## Normalized config flow

```text
raw config sources
  ↓
RawPackageConfig
  ↓
merge / normalize / validate
  ↓
ValidatedPackageConfig
  ↓
workflow payload resolution
  ↓
ResolvedWorkflowConfig
  ↓
RuntimeAssembly
  ↓
RuntimeDependencies + GraphRuntimeConfig
```

Runtime must not read raw config sources.
Runtime must consume validated / resolved config and runtime dependencies only.

`ValidatedPackageConfig.plugins.enabled` is an activation list for manually registered plugins, not an import or install mechanism.

## Relationship to existing payloads

- Package-level config: deployment / provider / plugin / policy / store / observability defaults
- `Workflow.definition_payload`: workflow instance-specific config
- `Run.input_payload`: execution input, not config override
- Normalized runtime config: package config plus validated `Workflow.definition_payload`

Do not mix these layers.

## P1-B done when

- RawPackageConfig / ValidatedPackageConfig / ResolvedWorkflowConfig are defined.
- RuntimeAssembly / RuntimeDependencies / GraphRuntimeConfig are related to the schema boundary.
- source precedence is fixed.
- versioning is fixed.
- unknown field policy is fixed.
- secret / env var reference handling is fixed.
- name-based resolution boundaries are fixed.
- workflow-specific config is separated from core schema.
- validation layering is defined.
- config validation / registry lookup / runtime assembly remain unimplemented.


## Config Core Block B

Config Core Block B implements the raw/normalized boundary for Mapping input only.

Supported top-level fields:

- `version`
- `environment`
- `plugins`
- `providers`
- `tools`
- `stores`
- `event_sinks`
- `limits`
- `observability`
- `safety`
- `metadata`

Rules:

- unknown core top-level fields are rejected
- plugin-specific mappings remain opaque to the config core
- secret references are retained, not resolved
- config cannot disable safety, redaction, or safe errors
- config cannot enable `allow_all_tools`
- config cannot provide arbitrary import / callable paths


## Config Validation Block C

`ConfigValidator` validates normalized config against the plugin registry through an `EffectivePluginSet` derived from `plugins.enabled`.

Rules:

- enabled plugins must be registered
- provider references must be provided by enabled plugins
- tools.allowlist must be provided by enabled plugins
- tools.configs must be a subset of tools.allowlist
- store backends must be provided by enabled plugins
- event sink backends must be provided by enabled plugins
- validation hooks are plugin-specific and run after registry lookup
- factory hooks are not called here


## Runtime Assembly Boundary

- config schema is loaded and normalized in Config Core
- config references are validated in Config Validation
- runtime assembly consumes `ValidatedPackageConfig`
- runtime assembly does not reinterpret raw config source
- runtime assembly does not perform registry lookup or plugin validation
