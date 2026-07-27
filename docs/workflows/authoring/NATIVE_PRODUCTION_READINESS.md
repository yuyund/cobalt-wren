# Native Production Readiness Checklist

- The workflow has typed input and output or explicit schemas.
- `native-validate` passes with representative input and the deployment configuration.
- Provider profiles, tools, artifact store, and event sinks are declared on the workflow.
- Secrets are environment references, not literal configuration values.
- Retried steps are safe to repeat or have application-level idempotency.
- Step names and occurrence keys contain no raw customer or secret data.
- Loops are bounded below the 1,000 step-occurrence limit.
- Synchronous timeout limitations are acceptable.
- Progress is monotonic and metrics use bounded, low-cardinality names.
- Process restart from the beginning is acceptable; durable resume is not required.
- External wheel build, entry-point discovery, and clean-room execution pass.
- Run UI, failure diagnostics, artifacts, progress, and metrics have been reviewed with production-like data.
