# Docs Subtree Guide

This subtree is the source of truth for documentation structure inside `docs/`.
Start at `index.md`, then follow the nearest folder `index.md` before reading deeper.

## Reading Order
1. `index.md`
2. The relevant folder `index.md`
3. The topic document itself

## Local Rules
- Keep links inside `docs/` relative.
- Prefer one topic per file.
- Add a folder `index.md` whenever a subfolder becomes a navigation target.
- When a topic grows across concerns, split it into smaller docs instead of expanding one file indefinitely.
- After changing docs structure, update the relevant `index.md` files and the docs tests in the same pass.
- Favor tight feedback loops: entry page, topic split, test coverage, then re-read the map.

## Top-Level Map
- `agent/`: Codex working rules and repo-operation guidance.
- `architecture/`: system shape, layer boundaries, and dataflow.
- `api/`: public facades and staged external surfaces.
- `configuration/`: config model, schema, and validation.
- `contracts/`: invariants, error taxonomy, and cross-cutting rules.
- `package/`: package completion, assurance, and verification docs.
- `plugins/`: plugin model, registration, and API shape.
- `workflows/`: workflow authoring and readiness.
- `roadmap/`: sequencing and completion gates.
- `assurance/`: safety contracts and assurance gaps.
- `adr/`: architecture decision records.
