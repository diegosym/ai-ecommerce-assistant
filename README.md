# Conversational Shopping Assistant

An anonymous shopping assistant that discovers products from natural-language requirements, supports multi-turn refinement and catalog-backed product Q&A, and provides conventional category/list/detail browsing. Every displayed product fact comes from the synthetic catalog; unsupported model output is rejected rather than rendered.

## Architecture

Two services share the OpenAPI contract in `specs/001-conversational-shopping-assistant/contracts/openapi.yaml`:

- **FastAPI backend** — validation, ephemeral conversation updates, deterministic fake provider port, lexical and pgvector hybrid retrieval, catalog hydration, structured telemetry, and evaluation scripts.
- **Next.js frontend** — responsive chat and catalog pages. Conversation state lives only in browser memory; reload and **New conversation** reset it.
- **PostgreSQL 16 + pgvector** — system of record for five categories/120 products and deterministic 1536-dimension fake embeddings.

The default retrieval mode is `lexical`. `AI_RETRIEVAL=hybrid` enables reciprocal-rank fusion of lexical and pgvector cosine-distance candidates. Structured requirements remain hard filters in both modes. No hosted provider is required or called by the default development, test, CI, or evaluation paths.

See [Architecture](docs/architecture.md), [ADRs](docs/adr/), and [demo evidence](docs/demo/index.md).

## Prerequisites

- Python 3.12+ and `uv`
- Node.js 22+ and npm
- Docker with Docker Compose
- Playwright Chromium for browser tests

## Install and seed

From this repository root:

```bash
uv sync --frozen
npm ci
npm ci --prefix frontend
POSTGRES_HOST_PORT=55434 docker compose up -d
uv run python -m scripts.migrate
uv run python -m scripts.seed_catalog
uv run python -m scripts.validate_catalog
uv run python -m scripts.generate_embeddings
```

The local database is exposed on **55434**. Host port 5432 is intentionally not used. The configuration defaults to:

```text
AI_PROVIDER=fake
AI_RETRIEVAL=lexical
DATABASE_URL=postgresql://assistant:assistant@localhost:55434/assistant_dev
LOG_RAW_CONTENT=false
```

No `.env.local` is needed for the fake-provider workflow. If you add one, do not commit it or any credentials.

## Run locally

Terminal 1 — FastAPI on **18000**:

```bash
AI_PROVIDER=fake AI_RETRIEVAL=lexical \
  uv run uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 18000
```

Terminal 2 — Next.js on **3000**:

```bash
ASSISTANT_API_URL=http://127.0.0.1:18000/api/v1 npm --prefix frontend run dev
```

Open `http://127.0.0.1:3000` for the assistant or `http://127.0.0.1:3000/catalog` for conventional browsing. The Next.js assistant proxy forwards requests to the configured backend. Catalog pages fetch through the same server-side base URL.

Host ports 8000 and 5432 are reserved for other local services in the development environment and are not required by this project.

## Checks

```bash
uv run pytest
uv run pytest backend/tests/contract
uv run ruff check backend
npm run check --prefix frontend
npx playwright install chromium  # once when the browser is absent
npm run test:e2e
```

The E2E configuration starts Uvicorn on 18000 and Next.js on 3000. Tests cover discovery, no-match relaxations, refinement, Q&A, stable references, reset semantics, catalog browsing, and phone/tablet/desktop layouts. `.github/workflows/ci.yml` runs equivalent migration, seed, backend, frontend, contract, and Playwright checks with the same pgvector image and no hosted credentials.

## Evaluation

The baseline was recorded before semantic/hybrid integration. Reproduce both runs with:

```bash
AI_RETRIEVAL=lexical uv run python -m scripts.evaluate \
  --retrieval lexical \
  --output data/evaluation/reports/baseline.md \
  --metrics-output data/evaluation/reports/baseline.metrics.json

AI_RETRIEVAL=hybrid uv run python -m scripts.evaluate \
  --retrieval hybrid \
  --output data/evaluation/reports/hybrid.md \
  --metrics-output data/evaluation/reports/hybrid.metrics.json \
  --compare-to data/evaluation/reports/baseline.metrics.json \
  --comparison-output data/evaluation/reports/comparison.md
```

Datasets are versioned synthetic draft fixtures with explicit provenance and contamination controls. Reports record catalog/dataset/provider/model versions and SC-001–SC-006. SC-001 is a constraint-satisfaction proxy, not human judging. SC-005 and SC-006 are **report-only** because thresholds and methodology approval are deferred. See the [final report](data/evaluation/reports/final.md).

## Optional hosted-provider smoke

The default fake provider is deterministic and credential-free. The opt-in script refuses to run with `AI_PROVIDER=fake`:

```bash
uv run python -m scripts.provider_smoke
```

A real hosted run requires explicit `AI_PROVIDER=openai`, server-side credentials/model/pricing configuration, and the optional official `openai` Python package. It was not executed in the deterministic development or CI environment. Never put hosted keys in client variables or source files.

## Observability and security

- Exactly one structured terminal event is emitted per accepted assistant interaction, including validation, catalog, and provider failures.
- Events include interaction/conversation IDs, latency, versions, outcome/error, and optional token/cost estimates; raw messages and full prompts are not logged.
- Known estimated costs can be aggregated by ephemeral `conversationId`; unknown costs remain unknown.
- Provider calls have configured deadlines and return typed `provider_unavailable` errors without partial product content.
- User messages, model output, and catalog text are untrusted. Product IDs and claims are validated, then display values are hydrated from the catalog.
- No checkout, orders, accounts, store-policy answers, persistent conversation store, cookies, or localStorage conversation history is provided.

## Documentation map

- `specs/001-conversational-shopping-assistant/` — approved requirements, contract, model, plan, and tasks.
- `docs/architecture.md` — components and data flow.
- `docs/adr/` — two-service split, pgvector, provider port, and ephemeral state decisions.
- `data/evaluation/` — fixtures and measured reports.
- `docs/demo/` — captured UI screenshots and transcript.
