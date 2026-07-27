# Observation Architecture Roadmap

## Before 0.1.0

- Preserve the three-layer architecture in ADRs.
- Fix the schema ID and compatibility policy.
- Test unknown-schema storage, redaction, truncation, and generic rendering.
- Define the minimum `observability.coverage.v1` payload contract.
- Audit semantic proposals against existing canonical facts to avoid duplicate
  persistence.

## 0.1.x

- Emit `semantic.execution_unit.lifecycle.v1` from LangGraph tasks and
  LlamaIndex steps.
- Add run-level observability coverage to the common UI.
- Add a generic semantic renderer.

## 0.2

- Add safe state snapshots, checkpoint correlation, route decisions, and
  interaction lifecycle projections.
- Experiment with inspection capabilities behind a non-public interface.
- Introduce a small specialized renderer registry.

## Later

- Structural state diffing.
- Graph descriptors.
- Replay and fork capability contracts.
- Post-run pull inspection.
- Framework-version compatibility matrices.
