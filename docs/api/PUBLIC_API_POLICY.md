# Public API Policy

## Stability domains

Cobalt Wren separates API stability into explicit domains.

| Domain | Status for 0.1.x | Contract |
|---|---|---|
| `cobalt_wren.api.llm` | Public | Provider-neutral LLM protocol and safe result types |
| `cobalt_wren.api.tools` | Public | Tool registry, result, and policy contracts |
| `cobalt_wren.api.stores` | Public, evolving | Artifact and checkpoint store protocols and DTOs |
| `cobalt_wren.api.events` | Public | Framework-neutral event sink protocol |
| `cobalt_wren.api.errors` | Public | Error classes, safe codes, retryability metadata |
| `cobalt_wren.api.plugins` | Public | Plugin metadata, contributions, discovery entry point |
| `cobalt_wren.api.workflow` | Public | Workflow definition, build, execution, and resume DTOs |
| `cobalt_wren.api.integrations` | Provisional SPI | Framework-neutral integration capability and projection DTOs |
| `cobalt_wren.api.engine` | Provisional facade | Engine creation and prepared workflow operations |
| `cobalt_wren.native` | Provisional authoring API | Ordinary-Python workflow authoring and observed step helpers |
| `cobalt_wren.integrations.*` | Concrete/internal | Concrete adapters and backends; no compatibility guarantee |
| `cobalt_wren.apps.*` | Internal control plane | Django models, services, views, and rendering |
| `cobalt_wren.config.*` | Internal/config-facing | Deployment bootstrap and validated configuration |
| `cobalt_wren.runtime.*` | Internal | Runtime assembly implementation |

## Compatibility rules

For the 0.1.x line:

- Public facade symbols are not removed or renamed without a deprecation period.
- Additive optional dataclass fields and new protocol methods with safe defaults may be introduced.
- Provisional surfaces may change in a minor release, but changes require release notes and migration guidance.
- Concrete provider, framework, and storage adapter modules are not stable import paths.
- Product renames do not rewrite persisted schema IDs, event kinds, workflow kinds, database identities, or plugin API versions.
- Exception `code` values are machine contracts and must not be reused with a different meaning.
- CLI success is exit code `0`, expected command/validation failure is `1`, and invocation/usage failure is `2`.
- Unknown integration projection schemas must remain storable and generically renderable.

## Import rules for consumers

Application and plugin packages should import only from:

```text
cobalt_wren.api.*
cobalt_wren.native
```

A consuming application may explicitly import a concrete adapter when it owns
that adapter dependency and accepts its provisional status. Generic workflow
packages should not import Django control-plane modules, runtime assembly,
plugin registry internals, or configuration loaders.

## Dependency ownership

Cobalt Wren does not own the installation or version policy of model SDKs or
workflow frameworks. Consumers declare LiteLLM, LangGraph, LlamaIndex Workflows,
or other provider/framework distributions directly.

PostgreSQL support is optional and installed with:

```bash
pip install "cobalt-wren[postgres]"
```

The base distribution must import, execute Native workflows, and start with the
default SQLite configuration without `psycopg` installed.
