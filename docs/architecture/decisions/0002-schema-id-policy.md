# ADR 0002: Projection Schema ID and Versioning Policy

- Status: Accepted
- Date: 2026-07-27

## Format

Schema IDs use lowercase dot-separated names and a terminal major version:

```text
<namespace>.<concept>.v<major>
```

Namespaces:

- `semantic`: framework-independent meaning
- `observability`: instrumentation and coverage metadata
- `langgraph`: LangGraph-native detail
- `llamaindex`: LlamaIndex Workflows-native detail
- `native`: Cobalt Wren Native authoring detail
- integration IDs owned by external distributions

## Compatibility

A schema major version changes when a consumer cannot safely interpret the new
payload using the previous contract. Additive optional fields do not require a
major version change. Existing payload meaning must not be silently redefined.

Schema IDs are data contracts. Renaming the product, Python package, or provider
implementation does not rewrite previously persisted schema IDs.

## Safety

Every projection payload must be JSON-compatible, bounded, redacted, and carry
truncation metadata through the persistence layer. Raw framework objects and
secrets are rejected or summarized before persistence.

## Rendering

Unknown schema IDs use the generic structured renderer. Specialized renderers
must fall back safely when fields are absent or a newer additive payload is
encountered.
