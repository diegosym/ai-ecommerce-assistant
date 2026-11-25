# Quickstart: Conversational Shopping Assistant

**Feature**: [spec.md](./spec.md)  
**Plan**: [plan.md](./plan.md)

> **Current status**: this is the required developer experience for the planned implementation. The repository contains the Spec Kit planning files; application code is being rebuilt as a FastAPI backend + Next.js frontend, so some commands below may not be executable until their task lands.

## 1. Planned Prerequisites

- Python 3.12+ with `uv` (or pip + venv) for the backend
- Node.js 22+ LTS and npm for the frontend
- Git
- Docker and Docker Compose for the local PostgreSQL + pgvector service (pinned image version)
- No authentication provider
- No hosted credentials for the deterministic fake-provider journey

After implementation, exact dependency versions will be pinned in the committed lockfiles (`uv.lock` and `package-lock.json`). Hosted chat/embedding model IDs will be explicit environment configuration and recorded in evaluation reports.

## 2. Install

From the repository root (`portfolio/ai-ecommerce-assistant/`):

```bash
# backend
uv sync
cp .env.example .env.local
# frontend
cd frontend && npm ci && cd ..
# database
docker compose up -d
```

The default `.env.local` development configuration must use:

```dotenv
AI_PROVIDER=fake
AI_RETRIEVAL=lexical
# Local PostgreSQL + pgvector (docker compose). The example below assumes the
# default host port 5432; if another PostgreSQL already occupies it (as in the
# current workspace, where it runs on 55434), start with POSTGRES_HOST_PORT=<free-port>
# and point DATABASE_URL at that port.
DATABASE_URL=postgresql://assistant:assistant@127.0.0.1:5432/assistant_dev
LOG_RAW_CONTENT=false
```

Do not commit `.env.local` or any real credential.

## 3. Validate Local Data

```bash
uv run python -m scripts.migrate
uv run python -m scripts.seed_catalog
uv run python -m scripts.validate_catalog
uv run python -m scripts.generate_embeddings
```

Expected behavior after implementation:

- `scripts.migrate` creates or upgrades the PostgreSQL schema (including the pgvector extension) idempotently.
- `scripts.seed_catalog` loads the versioned JSON catalog into PostgreSQL and reports catalog version, product count, category count, and provenance status.
- The completed catalog contains 100–200 synthetic products in 4–6 categories.
- `scripts.generate_embeddings` upserts one vector row per product, bound to the catalog content digest and model metadata.
- Fake-provider embeddings are deterministic and require no network.

A stale or incompatible embedding artifact must fail closed rather than silently search another catalog version.

## 4. Run the Application

Two processes (backend API + frontend):

```bash
# terminal 1 — API on http://localhost:18000
# (port 8000 may be occupied by a foreign service in some environments;
#  pick any free port and keep the frontend API base URL in sync)
uv run uvicorn app.main:app --reload --port 18000 --app-dir backend

# terminal 2 — frontend on http://localhost:3000
cd frontend && npm run dev
```

Open `http://localhost:3000`. The frontend calls the API through the contract in `contracts/openapi.yaml`; API base URL is configuration (default `http://localhost:18000`).

The first walking-skeleton acceptance journey is:

1. Load a non-empty catalog from the versioned local data.
2. Submit one natural-language product request through `POST /api/v1/assistant/interactions`.
3. Receive a schema-valid response using the fake provider.
4. Verify that every displayed product value equals the corresponding catalog record.
5. Verify one structured interaction telemetry event.

## 5. Required Checks

```bash
uv run pytest                 # backend: unit + contract + integration
cd frontend && npm run check  # frontend: lint, typecheck, unit tests
npm run test:e2e              # Playwright against both services
```

`uv run pytest` and `npm run check` must run without calling a hosted provider.

For a new development machine, install the Playwright browser once when needed:

```bash
npx playwright install chromium
npm run test:e2e
```

The E2E suite must cover at least:

- Discovery with catalog-valid recommendations.
- Explicit no-match and computed relaxation behavior.
- Multi-turn refinement and preference replacement.
- Product Q&A and unavailable information.
- Stable ordinal references.
- New-conversation and full-reload reset.
- Category/list/detail/filter navigation and empty-filter clearing.
- Phone, tablet, and desktop layouts.

## 6. HTTP Smoke Checks

With both development processes running:

```bash
curl --fail http://localhost:18000/api/v1/catalog/categories
curl --fail 'http://localhost:18000/api/v1/catalog/products?categoryId=headphones&maxPriceMinor=15000&currency=USD'
```

An empty filtered result is a successful response with `items: []`, not an error or blank page.

Create an initial assistant interaction:

```bash
curl --fail http://localhost:18000/api/v1/assistant/interactions \
  -H 'content-type: application/json' \
  -d '{
    "conversation": {
      "conversationId": "00000000-0000-4000-8000-000000000001",
      "createdAt": "2026-11-25T00:00:00.000Z",
      "turns": [],
      "preferences": [],
      "presentedProducts": []
    },
    "message": "I need wireless headphones with noise cancellation for $150."
  }'
```

The response must conform to `contracts/openapi.yaml`. Prices and attributes in `presentations` must match the loaded catalog; they are not authoritative when supplied by the model or client.

## 7. Evaluation Workflow

Run the deterministic baseline before semantic or hosted-model integration:

```bash
uv run python -m scripts.evaluate --retrieval lexical \
  --output data/evaluation/reports/baseline.md \
  --metrics-output data/evaluation/reports/baseline.metrics.json
```

After the candidate integration is configured:

```bash
uv run python -m scripts.evaluate --retrieval hybrid \
  --output data/evaluation/reports/hybrid.md \
  --metrics-output data/evaluation/reports/hybrid.metrics.json \
  --compare-to data/evaluation/reports/baseline.metrics.json \
  --comparison-output data/evaluation/reports/comparison.md
```

Each report must record:

- Catalog, dataset, prompt, provider, and model versions.
- Discovery relevance/catalog validity (SC-001).
- Q&A correctness (SC-002).
- Insufficient-evidence handling (SC-003).
- Latency distribution and workload (SC-004).
- Recall@K/relevance baseline comparison (SC-005).
- Refinement success without repeated requirements (SC-006).

SC-005 and SC-006 are reports, not release gates, until their numeric targets and evaluation methodology are approved. Hosted-model evaluations must record variance and must not be represented as deterministic unit tests.

## 8. Optional Hosted Provider

Real provider use is explicit opt-in. Configure server-only values in `.env.local`:

```dotenv
AI_PROVIDER=openai
OPENAI_API_KEY=<your-server-only-key>
OPENAI_CHAT_MODEL=<approved-model-id>
OPENAI_EMBEDDING_MODEL=<approved-embedding-model-id>
MODEL_PRICING_VERSION=<documented-pricing-version>
LOG_RAW_CONTENT=false
```

Then regenerate embeddings and run the opt-in smoke/evaluation commands documented by the implementation:

```bash
uv run python -m scripts.generate_embeddings
uv run python -m scripts.provider_smoke
uv run python -m scripts.evaluate --retrieval hybrid \
  --output data/evaluation/reports/hybrid.md \
  --metrics-output data/evaluation/reports/hybrid.metrics.json
```

Anonymous user text and minimal synthetic catalog evidence will be sent to the configured provider. Do not enter personal, customer, production, or confidential data. Estimated cost is operational metadata, not a billing statement.

## 9. Conversation Reset Semantics

No reset endpoint or persisted session is required:

- **New conversation**: the browser replaces `conversationId` and clears turns, preferences, and presented-product references.
- **Full reload**: the browser creates a new empty `ConversationState`.
- **No cross-visit memory**: cookies, local storage, and server-side conversation history are not used.

Telemetry may contain the ephemeral conversation ID for cost aggregation, but not raw conversation content by default.

## 10. Troubleshooting

| Symptom | Required action |
|---|---|
| Missing hosted credentials | Use `AI_PROVIDER=fake`; do not put keys in client variables or source files. |
| Stale embedding/catalog digest | Regenerate embeddings explicitly; do not bypass compatibility validation. |
| PostgreSQL unavailable | Run `docker compose up -d` and confirm migration/seed completed before starting the app. |
| No exact product match | Confirm the response is `no_match` with computed relaxations, not fabricated products. |
| Catalog empty or invalid | Fix/rebuild the versioned synthetic source; the assistant must return `unavailable`. |
| Hosted provider timeout | Preserve the typed error and telemetry event; do not return partial unverified content. |
| Context unexpectedly survives reload | Stop the affected slice and fix the reset behavior before claiming FR-013 compliance. |
