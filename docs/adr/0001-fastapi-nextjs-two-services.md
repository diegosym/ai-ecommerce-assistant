# ADR 0001: Split FastAPI and Next.js services

## Status

Accepted (2026-11-25).

## Context

The project needs Python-first AI evaluation/retrieval libraries and a responsive React storefront. A TypeScript monolith would make the Python AI ecosystem harder to use; Python-rendered UI would add unnecessary frontend work.

## Decision

Use FastAPI for domain logic, data access, provider integration, retrieval, telemetry, and evaluation, and Next.js for chat/catalog presentation. Communicate only through the versioned OpenAPI contract.

## Consequences

- Python and TypeScript dependency/tooling boundaries remain explicit and independently testable.
- Playwright must exercise two processes, adding some local/CI orchestration.
- No extra gateway, queue, or microservice fleet is introduced; service count remains two.
