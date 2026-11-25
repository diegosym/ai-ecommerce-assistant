# Implementation Plan: Conversational Shopping Assistant

**Branch**: `001-conversational-shopping-assistant` | **Date**: 2026-11-25 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-conversational-shopping-assistant/spec.md`

**Note**: This plan follows the `/speckit.plan` workflow. It does not authorize implementation or create `tasks.md`.

## Summary

Deliver an anonymous, responsive web store with conventional catalog browsing and a conversational shopping assistant. The assistant will interpret natural-language requirements, retrieve relevant products, preserve active-conversation preferences, answer catalog-backed questions, and render stable product references. A reload or explicit new conversation resets all conversational state.

The technical approach is a two-service application: a Python 3.12+ FastAPI backend and a Next.js frontend, communicating through the versioned REST contract in `contracts/openapi.yaml`. This split follows the explicit portfolio decision (2026-11-25) to keep the AI engineering stack Python-first (Ragas, LangSmith, Langfuse, DeepEval, OpenTelemetry are Python ecosystems) while retaining Next.js as the responsive chat/catalog UI. Both services share PostgreSQL 16+ with the pgvector extension as the system of record, seeded from a validated, versioned JSON catalog that remains the reviewable provenance source, per the portfolio decision to demonstrate relational and vector database design from the MVP. A deterministic lexical/filter baseline will be evaluated before semantic retrieval or hosted LLM integration. Hybrid retrieval will combine SQL structured filters, lexical ranking, and pgvector cosine similarity, fused by deterministic rank fusion. A provider port supports a deterministic fake and an initial hosted provider. Product facts will be hydrated from catalog records by ID, never trusted from generated text. Structured telemetry will support per-interaction measurements and per-conversation cost aggregation.

The implementation sequence will establish evaluation fixtures and the deterministic baseline first, then deliver independently testable vertical slices for discovery, catalog browsing, refinement, Q&A, and presentation. This document defines the design only; implementation remains gated by plan approval and `/speckit.tasks`.

## Technical Context

**Language/Version**: Backend Python 3.12+ (FastAPI, Pydantic v2); frontend Node.js 22+ LTS with TypeScript 5.x and Next.js. Exact dependency versions pinned by committed lockfiles (`uv.lock` or `requirements.txt`, `package-lock.json`).

**Primary Dependencies**: Backend: FastAPI, Pydantic, uvicorn, asyncpg or psycopg, pytest, httpx, openai (opt-in only). Frontend: Next.js App Router, React, Zod, Vitest, Testing Library, Playwright. Shared: PostgreSQL 16+ with pgvector, Docker Compose (pinned image version). Small retrieval utilities may be added only after the baseline justifies them.

**Storage**: PostgreSQL with pgvector as the system of record for catalog entities and product embeddings, seeded from versioned JSON files that carry provenance; evaluation fixtures as versioned files; ephemeral browser-held conversation state; structured telemetry to stdout. No authentication store and no cross-visit conversation persistence.

**Testing**: Backend pytest (unit, contract, integration) with httpx TestClient against the OpenAPI contract; frontend Vitest + Testing Library for components and Playwright responsive E2E across both services; deterministic fake-provider tests; reproducible evaluation scripts with versioned datasets.

**Target Platform**: Modern phone, tablet, and desktop browsers; Python runtime for the API plus Node.js for frontend development; two local processes (uvicorn + Next.js dev server) for development, one containerized API process for the demonstration deployment.

**Project Type**: Full-stack web application; two services (FastAPI backend + Next.js frontend) over a versioned REST contract in one repository.

**Performance Goals**: P95 assistant response within 5 seconds under the approved evaluation workload (SC-004). Retrieval and rendering budgets will be measured separately from provider latency. No throughput target is claimed before a workload is agreed.

**Constraints**: English only; anonymous use; catalog-only facts; explicit unavailable/no-match behavior; no standalone natural-language catalog search; context resets on reload/new conversation; no real customer or production data; provider inputs and outputs are untrusted; no consequential tools or purchases.

**Scale/Scope**: Synthetic consumer-electronics catalog of 100–200 products in 4–6 categories; small relevance-ranked recommendation sets; five user stories (US1–US5); one active browser conversation at a time per tab; no production scaling objective.

## Constitution Check

*GATE: Required before Phase 0 research and re-checked after Phase 1 design.*

| Gate | Before Phase 0 | After Phase 1 design | Evidence / enforcement |
|---|---|---|---|
| Approved requirements before implementation | PASS for planning | PASS for planning | Spec quality checklist is complete. Implementation still requires explicit spec/plan approval and tasks. |
| End-to-end, independently demonstrable capability | PASS | PASS | Walking skeleton followed by vertical slices; each story has an independent test in `spec.md`. |
| Spec → task → code → test traceability | PASS | PASS | Contracts and model reference FR/US IDs; `/speckit.tasks` must preserve these IDs. |
| AI baseline before integration | PASS | PASS | Lexical/filter baseline and evaluation fixtures precede semantic and hosted-model integration. |
| Measurable AI quality and regression evaluation | PASS | PASS | Discovery, Q&A, insufficient-evidence, retrieval, and refinement runners map to SC-001–SC-006. |
| Versioned, representative, authorized datasets | PASS | PASS | Synthetic catalog and evaluation fixtures carry version, provenance, generation method, and review metadata. |
| Reproducibility and observability | PASS | PASS | Lockfile, catalog/prompt/model/dataset versions, deterministic fake, latency/token/error/cost events, and conversation aggregation keys. |
| Security and privacy by design | PASS | PASS | Schema validation, bounded inputs, output validation, prompt/content separation, no tools, credential isolation, and no raw-message logging by default. |
| Minimal complexity | PASS | PASS | Two services only (FastAPI + Next.js) justified by the portfolio Python-first decision and the existing REST contract; one Postgres service (catalog + vector index); stateless HTTP; only external-integration adapters. |
| Honest quality checks | PASS | PASS | Quickstart distinguishes current planning commands from the developer interface required after implementation. |

**Gate result**: PASS for the planning phase. No constitutional violation requires Complexity Tracking. This is not approval to implement.

## Phase 0: Research Outcomes

All planning unknowns are resolved in [research.md](./research.md); no `NEEDS CLARIFICATION` markers remain.

Key decisions:

1. Split into a FastAPI backend and a Next.js frontend over the shared `contracts/openapi.yaml` REST contract (portfolio decision 2026-11-25: Python-first AI stack); the earlier single-process TypeScript design was superseded before US1 implementation.
2. Store the catalog in PostgreSQL with pgvector (system of record), seeded from validated versioned JSON; this reflects the explicit portfolio decision to demonstrate relational and vector database design from the MVP.
3. Establish lexical/filter evaluation baselines before adding embeddings or hosted generation.
4. Use a narrow provider port with deterministic fake and OpenAI implementations; model IDs and prompts are versioned configuration, not hard-coded facts.
5. Keep conversation state in the browser and validate the complete state on every request; reload/new conversation clears it.
6. Hydrate every displayed product fact from the catalog and reject unsupported model-produced claims.
7. Use structured stdout events without raw user messages by default; aggregate cost by ephemeral conversation ID.
8. Treat comparisons and store-policy/FAQ assistance as later features despite their broader Product Brief MVP wording.

## Phase 1: Design

### Runtime flow

```text
Browser conversation state + user message
                  │
                  ▼
       Request schema and size validation
                  │
                  ▼
 Intent/preferences extraction (fake or hosted LLM)
                  │
                  ▼
 Validated CustomerPreference updates
                  │
                  ▼
 Structured filters ──► eligible catalog records
                  │
                  ▼
 Lexical baseline + semantic candidates ──► hybrid rank
                  │
                  ▼
 Evidence bundle containing only selected catalog fields
                  │
                  ▼
 Constrained response selection/generation
                  │
                  ▼
 Output validation + catalog hydration + stable references
                  │
                  ▼
 Assistant response + product cards + telemetry event
```

If structured eligibility is empty, the assistant returns an explicit no-match response and identifies relaxable criteria. If the catalog is empty/unavailable or evidence is insufficient, it returns an unavailable response rather than invoking the model to invent an answer. Out-of-scope requests bypass retrieval and receive a transparent boundary response.

### Grounding boundary

- The catalog is the sole source of product facts.
- The model may classify intent, extract preferences, select evidence fields, and produce constrained conversational text.
- Product IDs returned by the model must belong to the supplied evidence bundle.
- Names, prices, attributes, and availability labels are rendered from server-side catalog records.
- Any model-produced factual claim that cannot be validated is discarded; the response falls back to deterministic unavailable/clarification wording.
- Customer statements remain preferences or beliefs and never replace catalog values.

### Conversation and reset design

The browser owns an ephemeral `ConversationState` containing a random conversation ID, ordered turns, active preferences, and ordinal-to-product reference mappings. Each assistant request sends the required state through a validated, size-bounded contract. The server treats it as untrusted input, reconstructs valid preferences, and recomputes grounding.

“New conversation” replaces the ID and clears all state. A full page reload creates a new empty conversation. No cookie, local storage, session store, or server-side history is used. Telemetry retains only the ephemeral ID and operational measurements for the configured log retention, never conversational content by default.

### Evaluation and release gates

- **Discovery**: relevance and catalog validity, target ≥85% (SC-001).
- **Q&A**: correctness against golden answers, target ≥90% (SC-002).
- **Insufficient evidence**: correct decline/unavailable behavior, target ≥95% (SC-003).
- **Latency**: P95 ≤5 seconds under an approved workload (SC-004).
- **Retrieval**: Recall@K and relevance reported against a baseline; numeric release target deferred (SC-005).
- **Refinement**: successful changes without repeated requirements reported; “majority” must be replaced by an approved numeric threshold before use as a release gate (SC-006).

The lexical/filter baseline runs before semantic retrieval and before hosted LLM integration. Each addition must retain or improve the approved capability metrics, with variance recorded where hosted-model results are non-deterministic. Evaluation datasets, contamination controls, workload, and acceptance conditions require approval before release-gate use.

### Security, privacy, and failure behavior

- Validate request bodies, conversation state, product IDs, filters, model outputs, and response payloads with explicit schemas and limits.
- Delimit catalog content and user text as untrusted data in prompts; neither can alter system instructions.
- Do not expose model tools, checkout, order, account, or administrative capabilities.
- Keep provider credentials server-side and document that anonymous user text and synthetic evidence are sent to the configured hosted provider.
- Do not log raw messages, credentials, or full prompts by default.
- Apply provider timeouts and bounded output tokens; return typed unavailable/error responses without partial fabricated content.
- Validate catalog provenance and embedding metadata at startup/build time; incompatible caches fail closed and are regenerated through an explicit command.

### Scope interpretations

- A catalog `warranty` attribute may be answered as a product fact; store warranty policies or warranty documents remain out of scope.
- Conventional filters are deterministic and contain no semantic or natural-language search parameter.
- FR-014 receives direct contract/integration tests for every interaction, including failures.
- Cost is emitted per interaction and aggregated by `conversationId` to satisfy the Product Brief’s per-conversation measurement.

### Requirement Coverage

| Scope | Planned design and verification |
|---|---|
| US1; FR-001–FR-003, FR-007 | Preference extraction, structured eligibility, hybrid retrieval, catalog hydration, discovery/no-match integration and evaluation tests. |
| US2; FR-005, FR-006, FR-013 | Validated browser-held state, slot-based preference replacement, stable references, and reload/new-conversation E2E reset tests. |
| US3; FR-004, FR-006–FR-007 | Evidence-bound response selection, unavailable fallbacks, golden Q&A and insufficient-evidence evaluations. |
| US4; FR-008–FR-009 | Hydrated product presentations, monotonically stable ordinals, responsive component and E2E tests. |
| US5; FR-009, FR-012 | Category/list/detail/filter routes and pages, no NL search parameter, empty-filter clearing tests. |
| FR-010–FR-011 | Anonymous typed API, deterministic out-of-scope outcomes, and no account/checkout/tool capabilities. |
| FR-014 | Terminal telemetry event tests for every outcome and per-conversation cost aggregation tests. |
| SC-001–SC-006 | Separate reproducible evaluation reports; deferred targets cannot be treated as approved release gates. |

No requirement is considered implemented by this table. `/speckit.tasks` must carry these identifiers into executable tasks and tests.

## Project Structure

### Documentation (this feature)

```text
specs/001-conversational-shopping-assistant/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── openapi.yaml
├── checklists/
│   └── requirements.md
└── spec.md
```

`tasks.md` is intentionally absent and will be created only by the separately approved `/speckit.tasks` phase.

### Source Code (repository root)

```text
backend/                      # FastAPI (Python 3.12+)
├── pyproject.toml
├── app/
│   ├── main.py               # FastAPI app factory
│   ├── api/v1/
│   │   ├── assistant/interactions.py
│   │   └── catalog/{categories,products}.py
│   ├── features/
│   │   ├── catalog/{domain,repository,postgres_repository}.py
│   │   └── assistant/{domain,conversation_state,interaction_service,response_validator}.py
│   ├── lib/
│   │   ├── ai/{provider,fake_provider,openai_provider}.py
│   │   │   └── prompts/
│   │   ├── retrieval/{lexical,semantic,hybrid}.py
│   │   └── telemetry/{events,logger}.py
│   └── core/{config,validation}.py
├── scripts/                  # migrate, seed-catalog, validate-catalog,
│                              # generate-embeddings, provider-smoke, evaluate
└── tests/
    ├── unit/
    ├── contract/
    └── integration/

frontend/                     # Next.js (TypeScript)
├── package.json
└── src/
    ├── app/
    │   ├── page.tsx          # chat UI
    │   └── catalog/{page,[productId]/page}.tsx
    ├── features/
    │   ├── assistant/components/
    │   └── catalog/components/
    └── lib/api.ts            # typed client generated from/hand-kept against openapi.yaml

shared / repo root
├── data/
│   ├── catalog/catalog.json
│   └── evaluation/
├── db/migrations/001_init.sql
├── docker-compose.yml        # pinned PostgreSQL/pgvector service
├── docs/{adr/,architecture.md,demo/}
├── .github/workflows/ci.yml
└── tests/e2e/                # Playwright (starts both services)
```

**Structure Decision**: Two services over the existing REST contract. The FastAPI backend owns domain logic, retrieval, provider port, telemetry, and all data access; the Next.js frontend owns pages and conversational UI and talks to the backend only through `contracts/openapi.yaml`. This reflects the portfolio Python-first decision while keeping UI work in the framework that makes FR-009 cheap. A root-level `docker-compose.yml` runs the pinned PostgreSQL/pgvector service for development and integration tests. Service count is capped at two; no additional infrastructure (queues, gateways, vector DBs) is introduced.

## Verification Strategy

| Level | Required evidence |
|---|---|
| Unit | Preference replacement, stable references, filters, ranking merge, no-match relaxation, grounding validation, cost calculation. |
| Contract | OpenAPI request/response validation, bounded inputs, typed errors, no standalone query/search parameter. |
| Integration | PostgreSQL migration and seed, pgvector index round-trip, assistant routes with fake provider, catalog hydration, empty/unavailable catalog, provider timeout, telemetry on success and failure. |
| E2E | Discovery, refinement, Q&A, product references, catalog browsing/filter clearing, responsive layouts, reload/new-conversation reset. |
| Evaluation | Versioned discovery, Q&A, insufficient-evidence, retrieval, and refinement fixtures; baseline and candidate reports. |
| Reproducibility | Clean install, catalog validation, deterministic fake journey, test suite, evaluation command, and documented real-provider opt-in. |

## Complexity Tracking

No violations to justify.
