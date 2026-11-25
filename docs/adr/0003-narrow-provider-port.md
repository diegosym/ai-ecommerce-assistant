# ADR 0003: Keep a narrow, deterministic provider boundary

## Status

Accepted (2026-11-25).

## Context

Tests and local development must be credential-free and reproducible, while intent extraction and response selection may later use a hosted model. Direct SDK calls throughout domain logic would leak provider details and make failures nondeterministic.

## Decision

Expose a narrow Python protocol for preference/question extraction and evidence-bound response selection. Use a deterministic fake by default. Apply configured deadlines in the service path and return typed provider errors. Hosted smoke is explicit opt-in only.

## Consequences

- Unit, integration, CI, E2E, and evaluation runs need no hosted credentials or network.
- Provider-specific types do not enter domain models.
- The fake validates orchestration and grounding, not hosted model quality.
- Future hosted adapters must preserve the same timeout, grounding, and telemetry boundaries.
