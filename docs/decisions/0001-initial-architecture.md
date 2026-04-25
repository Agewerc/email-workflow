# ADR 0001: Initial Architecture

## Decision

Use a file-backed, src-layout Python package with:

- a workflow registry and runner
- explicit provider interfaces
- reusable renderers/templates
- a lightweight FastAPI admin surface
- Citizen Brief as the first concrete workflow

## Rationale

This keeps the first version simple while preserving a clean path to multiple workflows and better operational tooling.
