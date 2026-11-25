# Architecture

## Goals and boundaries

The application demonstrates catalog-grounded shopping assistance without authentication, persistent conversation history, hosted credentials, or consequential shopping tools. FastAPI owns facts and orchestration; Next.js owns presentation. PostgreSQL is the only product-fact store.

## Components

```text
┌────────────────────────────── Browser ──────────────────────────────┐
│ Chat UI + catalog UI                                                │
│ Ephemeral ConversationState in memory only (no cookies/localStorage)│
└──────────────────────────────┬───────────────────────────────────────┘
                               │ JSON / OpenAPI
                               ▼
┌──────────────────────── Next.js frontend :3000 ─────────────────────┐
│ Assistant same-origin proxy + server-rendered catalog pages        │
└──────────────────────────────┬───────────────────────────────────────┘
                               │ ASSISTANT_API_URL
                               ▼
┌──────────────────────── FastAPI backend :18000 ─────────────────────┐
│ Request/state validation                                            │
│ Fake provider port with deadline                                    │
│ Preference replacement + stable ordinals                            │
│ Lexical filters/ranking ─┐                                          │
│ pgvector ranking ────────┴─ RRF hybrid (opt-in)                     │
│ Response validation + catalog hydration                             │
│ Typed errors + one terminal telemetry event per interaction         │
└──────────────────────────────┬───────────────────────────────────────┘
                               │ psycopg
                               ▼
┌──────────────────── PostgreSQL :55434 ──────────────────────────────┐
│ catalog_metadata / categories / products / product_embeddings      │
└──────────────────────────────────────────────────────────────────────┘
```

## Assistant data flow

```text
Client state + message
  → bounded request validation (failure → typed 400 + one error event)
  → deterministic intent/preference/question extraction (deadline enforced)
  → same-slot replacement; active requirements only
  → discovery, Q&A, clarification, no-match, or out-of-scope branch
  → structured eligibility
  → lexical candidates, optionally fused with pgvector candidates
  → provider response proposal checked against evidence IDs/claims
  → product values hydrated from current PostgreSQL records
  → stable presentation references + response + one telemetry event
```

Out-of-scope requests receive a transparent decline. Missing products/attributes produce `unavailable`; unknown model IDs and altered claims fall back to deterministic grounded wording. Provider deadline expiry produces typed `provider_unavailable` with no partial content.

## Catalog data flow

Conventional category/list/detail routes call `CatalogRepository`. Product filters accept only category, minor-unit price bounds, currency, and pagination. No text or semantic search parameter exists on catalog endpoints or UI. Empty results are successful `items: []` responses and render a clear action.

## State and privacy

The browser sends the complete bounded `ConversationState` on each turn. The server validates it but never stores it. New conversation and reload replace the ID and all turns/preferences/references. Telemetry stores operational metadata only; estimated costs may be aggregated by ephemeral conversation ID, while raw content is excluded.

## Retrieval and artifact compatibility

The lexical baseline was evaluated before hybrid code. Hybrid mode computes pgvector cosine-distance candidates only after validating every embedding's catalog version, content digest, dimensions, and product coverage. Missing or stale artifacts fail closed. RRF uses deterministic product-ID tie-breaking; it does not relax explicit category/budget/attribute requirements.

## Verification and delivery

Backend unit/contract/integration tests use fake providers and local PostgreSQL. Playwright covers both services and responsive UI. Evaluation datasets/reports are versioned separately from tests. CI reproduces install, migration, seed, backend/frontend checks, contract tests, and browser journeys without hosted credentials.
