# ADR 0002: Include PostgreSQL and pgvector in the MVP

## Status

Accepted (2026-11-25).

## Context

The portfolio requires relational modeling and vector retrieval. Separate JSON, relational, and vector stores would create consistency boundaries and obscure catalog-version compatibility.

## Decision

Use PostgreSQL 16 with pgvector as the system of record for catalog metadata, categories, products, and deterministic embedding artifacts. Seed it from the versioned synthetic JSON catalog. Establish lexical evaluation before enabling pgvector hybrid retrieval.

## Consequences

- One transaction/consistency boundary covers product facts and derived vectors.
- Embeddings are rebuildable and fail closed on version/digest/dimension/coverage mismatch.
- Docker and migrations are required locally and in CI.
- RRF hybrid results are measured against the recorded lexical baseline rather than assumed better.
