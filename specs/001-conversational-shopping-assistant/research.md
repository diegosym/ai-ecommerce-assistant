# Phase 0 Research: Conversational Shopping Assistant

**Date**: 2026-11-25  
**Feature**: [spec.md](./spec.md)  
**Purpose**: Resolve technical choices required by `plan.md`. No implementation or external benchmark result is claimed.

## Research Method

The decisions below derive from the approved-scope requirements, the Product Brief, the constitution, the stated catalog scale, and established web/application testing patterns. No provider benchmark, latency measurement, or dataset quality result is available yet; those must be produced by the planned baselines and spikes. Exact package/model versions will be pinned and recorded during implementation rather than invented in this document.

## R1 — Application shape and runtime

**Decision**: Use two services in one repository: a Python 3.12+ FastAPI backend (API routes, domain, retrieval, provider port, telemetry, scripts, tests) and a Next.js App Router frontend (pages, conversational UI), communicating only through the versioned REST contract in `contracts/openapi.yaml`.

**Rationale**: This follows the explicit portfolio decision (2026-11-25) to keep the AI engineering stack Python-first — the evaluation and observability tooling targeted by the portfolio (Ragas, LangSmith, Langfuse, DeepEval, OpenTelemetry) is Python-native, and backend code is where the AI logic lives. Next.js is retained for the UI because FR-009 (responsive conversational web interface) is cheapest there. The OpenAPI contract already exists, so the split has a defined boundary from day one.

**Alternatives considered**:

- Single TypeScript/Next.js full-stack app (previous decision): superseded — it put the AI logic in TypeScript, misaligning with the portfolio's Python-first tooling goal; it was implemented only as far as the foundational layer before the change.
- Python backend plus server-rendered Python frontend (HTMX/Jinja): rejected because the responsive chat UI in FR-009 is materially harder and less demonstrable than with a React frontend.
- Python backend plus hand-rolled React SPA (Vite only): rejected as more build/tooling plumbing than Next.js for no benefit at this scope.
- Microservices or separate repositories: rejected; two services in one repository keeps the contract and CI simple.

**Validation**: The walking skeleton must start both services, render catalog data, and complete one assistant interaction through the public HTTP contract using the fake provider. Contract tests on the backend and Playwright E2E on the full stack enforce the boundary.

## R2 — Catalog representation and persistence

**Decision**: Store catalog entities (categories, products) and product embeddings in PostgreSQL 16+ with the pgvector extension as the system of record. Seed it from a validated, versioned JSON file that keeps carrying provenance and remains the reviewable data source; application code reads through a narrow `CatalogRepository` boundary.

**Rationale**: This follows the explicit portfolio decision (2026-11-25) to demonstrate relational and vector database design from the MVP. One Postgres service covers structured filtering, relational integrity (foreign keys, constraints), and cosine-similarity search without operating a separate vector store, while the JSON seed keeps datasets versionable and reviewable.

**Alternatives considered**:

- JSON plus in-process embeddings only: simpler, but does not demonstrate relational/vector database design, which the portfolio requires.
- SQLite with a vector extension: fewer moving parts, but weaker demonstration of mainstream relational/vector engineering and a less portable skill signal.
- Standalone vector database (Qdrant, Chroma, etc.): justified only with scale or advanced vector features; at 100–200 products pgvector keeps one service and one consistency boundary.
- ORM-heavy abstraction: deferred; start with explicit SQL and migrations, adding tooling only when it pays for itself.

**Validation**: Migration must enforce unique IDs, category foreign keys, money units, and provenance rows; seed-time schema validation must reject malformed products, missing provenance, and products outside the agreed catalog envelope. The final catalog size must be verified rather than assumed. Embedding rows must match catalog version, dimensions, and content digest or fail closed.

## R3 — Retrieval and baseline

**Decision**: Implement structured eligibility filters (SQL) and lexical ranking first, evaluate them, then add pgvector cosine-similarity candidates and deterministic hybrid fusion. Explicit requirements remain hard constraints; lexical and semantic scores rank eligible records. A separate diagnostic query may identify relaxable criteria after a no-match result.

**Rationale**: The Product Brief requires hybrid retrieval, while the constitution requires a baseline before AI integration. A lexical/filter baseline reveals whether semantic retrieval improves relevant discovery rather than adding it by assumption. Reciprocal-rank fusion over SQL lexical ranks and pgvector similarity ranks is deterministic, explainable, and does not require score calibration between incompatible lexical and embedding scales.

**Alternatives considered**:

- LLM-only product selection: rejected because it is not a reproducible retrieval baseline and increases hallucination risk.
- Semantic-only retrieval: rejected because exact category, price, and attribute constraints need deterministic handling.
- Weighted raw-score blending: deferred because lexical and embedding score distributions require calibration; rank fusion is simpler initially.
- Learned reranking: out of scope and unjustified until baseline reports demonstrate a need.

**Validation**: Publish Recall@K and relevance for the baseline and hybrid candidate on the same versioned discovery dataset. Semantic integration proceeds only with recorded evidence and an approved evaluation method.

## R4 — Model/provider boundary

**Decision**: Define a narrow `LanguageModelProvider` port (Python protocol/ABC) for preference extraction and constrained response selection. Provide a deterministic fake for tests and local development, plus an initial OpenAI implementation using the official `openai` Python SDK behind the same port. Configure chat and embedding model IDs through server-only environment variables and record them in telemetry/evaluation reports.

**Rationale**: The constitution requires justified provider coupling and reproducibility. A narrow port keeps provider-specific types in one adapter while the fake makes behavioral tests deterministic and credential-free. Using one initial hosted provider reduces operational variability; the abstraction covers only the two operations the application actually needs, not a general agent framework. Python keeps the adapter in the same ecosystem as the planned evaluation tooling.

**Alternatives considered**:

- Direct OpenAI SDK calls throughout application code: rejected because they leak provider types and make deterministic tests harder.
- LiteLLM or similar multi-provider abstraction: deferred — one provider behind our own narrow port is enough; adopt only when a second provider is actually evaluated.
- Multiple hosted providers in the first slice: rejected as unneeded comparison scope.
- Fully local models: deferred because hardware, quality, and latency characteristics have not been established.

**Data sharing**: Anonymous user text and the minimum synthetic catalog evidence required for a response may be sent to the configured provider. Raw messages are not logged by the application by default. Real personal or production data is prohibited by the spec.

**Validation**: Contract tests run entirely against the fake. A separately documented opt-in smoke test verifies the real provider, model IDs, timeout, token usage, and cost metadata.

## R5 — Conversation state

**Decision**: Keep `ConversationState` in browser memory and send validated state with each interaction. Use stateless HTTP requests. A reload or “New conversation” creates a new random ID and clears preferences, turns, and product-reference mappings.

**Rationale**: FR-013 explicitly forbids persistence across reloads and visits. Browser-held state satisfies that rule without a session database, cookies, or orphaned server-side conversations. Revalidation prevents the client from becoming a source of verified product facts.

**Alternatives considered**:

- Server in-memory sessions: rejected because they introduce lifecycle, cleanup, and single-instance coupling while still failing to add useful persistence.
- Cookie/localStorage persistence: rejected because it conflicts with mandatory reload reset and creates retention ambiguity.
- Sending unstructured chat history only: rejected as the sole state because preferences and ordinal references would be harder to validate and test deterministically.

**Validation**: E2E tests prove refinement, replacement, stable ordinals, explicit reset, reload reset, and absence of persisted browser storage. Contract tests reject malformed or oversized client state.

## R6 — Grounded response construction

**Decision**: Treat model output as a constrained proposal. Validate product IDs and evidence-field references, then hydrate all displayed product values from the catalog. Use structured response kinds and deterministic fallback messages for no-match, insufficient evidence, unavailable data, and out-of-scope requests.

**Rationale**: Grounding cannot be established by prompt wording alone. Catalog hydration makes the source of displayed facts explicit and testable, while typed fallback behavior prevents fabricated partial responses.

**Alternatives considered**:

- Free-form generated response with product names embedded: rejected because unsupported text cannot be reliably validated.
- Render raw model JSON directly: rejected because model output is untrusted.
- Fully deterministic assistant without an LLM: retained as the fake/baseline, but not the final conversational experience because flexible language interpretation is a core requirement.

**Validation**: Unit and integration tests inject unknown product IDs, altered prices, unsupported attributes, malformed output, prompt-injection text, and customer/catalog conflicts. Every factual UI value must resolve to the current catalog.

## R7 — Testing and evaluation

**Decision**: Use Vitest, Testing Library, and Playwright, plus standalone evaluation runners for discovery, Q&A, insufficient evidence, retrieval, and refinement. Keep golden datasets separate from implementation examples and record dataset/version metadata in every report.

**Rationale**: Deterministic application tests and non-deterministic model evaluations answer different questions. Separating them prevents a passing unit suite from being presented as evidence of assistant quality.

**Alternatives considered**:

- Hosted-model calls in every test: rejected due to cost, variance, credentials, and poor reproducibility.
- Manual conversational testing only: rejected because SC-001–SC-006 require repeatable evidence.
- Using the catalog seed examples as the only evaluation set: rejected because of contamination and inadequate coverage.

**Validation**: The evaluation design must define labeling rules, dataset splits/contamination controls, workload, K values, variance handling, and numeric gates. SC-005 and SC-006 cannot be release gates until their deferred targets are approved.

## R8 — Telemetry and cost

**Decision**: Emit one structured operational event per assistant interaction with interaction/conversation IDs, timestamps, latency stages, model/prompt/catalog/dataset versions where applicable, input/output tokens, estimated cost and pricing version, outcome, and typed error. Aggregate per-conversation cost by `conversationId` in log analysis. Do not emit raw messages or prompts by default.

**Rationale**: FR-014 and the constitution require operational evidence, while the Product Brief also requires per-conversation cost. stdout is sufficient for local/demo operation and compatible with later log collection without adding a telemetry database.

**Alternatives considered**:

- Client-only metrics: rejected because provider usage and server errors are not authoritative in the browser.
- Adding an observability vendor now: deferred until a deployment requires retained/queryable monitoring.
- Logging full prompts and responses: rejected by default because it increases sensitive-data exposure and is unnecessary for operational metrics.

**Validation**: Success, no-match, validation failure, provider failure, and catalog failure tests each assert one complete event. Cost aggregation tests prove interaction and conversation totals without treating estimated cost as billing truth.

## R9 — Dependency and reproducibility policy

**Decision**: Commit lockfiles for both services (`uv.lock` or `requirements.txt` for the backend, `package-lock.json` for the frontend), plus the environment example, catalog/evaluation data, prompts, and embedding metadata. Pin the PostgreSQL/pgvector Docker image version. Avoid exact version claims until the implementation manifests exist. Provide a fake-provider path that needs no credentials or network.

**Rationale**: Reproducibility comes from committed versions and procedures, not from unverified version numbers in a design document. Two lockfiles are the cost of the two-service decision and are checked by CI.

**Alternatives considered**:

- Floating dependency/model versions: rejected because evaluations would not be reproducible.
- Multiple package managers per service (poetry + npm + ...): rejected; one Python lockfile tool and npm keep contributor friction low.
- Mandatory hosted credentials for all local checks: rejected because it prevents deterministic offline verification.

**Validation**: A clean checkout must support install, `docker compose up -d`, migration/seed, validation, unit/integration tests, fake-provider E2E, and evaluation baselines using only documented commands.

## Resolved Planning Questions

No technical `NEEDS CLARIFICATION` remains for planning. The following are approval gates, not hidden assumptions:

1. Approval of this plan and the selected stack.
2. Approval of evaluation methodology and deferred SC-005/SC-006 thresholds before release-gate use.
3. Explicit opt-in and credentials before real hosted-provider calls.
4. Reconciliation at release planning between the broader Product Brief MVP and this feature’s explicit exclusions; this feature follows `spec.md`.
