# Tasks: Conversational Shopping Assistant

**Input**: Design documents from `/specs/001-conversational-shopping-assistant/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included because plan.md `Verification Strategy` and the Constitution explicitly require unit, contract, integration, E2E, and evaluation evidence for this feature.

**Organization**: Tasks are grouped by user story so each story can be implemented and tested independently.

**Architecture**: FastAPI backend + Next.js frontend over `contracts/openapi.yaml` (plan.md Structure Decision, 2026-11-25). Backend paths are Python; frontend paths are TypeScript.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US5)
- Include exact file paths in descriptions
- Field constraints are cited from `data-model.md` by `Entity.field`, not restated

## Path Conventions

Two services per plan.md: `backend/` (FastAPI, Python 3.12+, pytest), `frontend/` (Next.js, TypeScript, Vitest/Playwright), shared repo root (`data/`, `db/`, `docker-compose.yml`, `tests/e2e/`, `docs/`).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Two-service project initialization and basic structure

- [ ] T001 Restructure to the two-service layout per plan.md: create `backend/` FastAPI skeleton (pyproject.toml, app/main.py), move the Next.js app into `frontend/`, and retire the superseded monolith files (root package.json, src/lib/, src/features/, scripts/*.ts, TS test dirs) whose Python replacements arrive in T006–T013
- [ ] T002 [P] Configure linting and formatting: ruff for backend in `backend/pyproject.toml`; ESLint + Prettier for frontend in `frontend/eslint.config.mjs` and `frontend/.prettierrc`
- [ ] T003 [P] Add `docker-compose.yml` with pinned PostgreSQL 16 + pgvector image for the development database per plan.md Technical Context
- [ ] T004 [P] Add `.env.example` documenting AI_PROVIDER, AI_RETRIEVAL, DATABASE_URL, LOG_RAW_CONTENT, model IDs and MODEL_PRICING_VERSION per plan.md Technical Context
- [ ] T005 [P] Configure pytest for backend (`backend/pytest.ini` or pyproject tool section) and Vitest + Testing Library + Playwright for frontend (`frontend/vitest.config.ts`, `frontend/playwright.config.ts`, `frontend/tests/setup.ts`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Catalog storage, repository port, configuration and telemetry that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T006 Create `db/migrations/001_init.sql` implementing data-model.md §10 tables (catalog_metadata, categories, products, product_embeddings) with constraints from data-model.md Product.id, Product.categoryId, Product.price, Money.amountMinor, Money.currency, product_embeddings.catalog_version, product_embeddings.embedding
- [ ] T007 [P] Implement `backend/scripts/migrate.py` idempotent migration runner enabling the pgvector extension per data-model.md §10 physical rules
- [ ] T008 Author `data/catalog/catalog.json` synthetic catalog (100–200 products, 4–6 categories) with fields per data-model.md CatalogDocument and CatalogProvenance
- [ ] T009 Implement `backend/scripts/validate_catalog.py` validating data-model.md CatalogDocument, CatalogProvenance, Category, AttributeDefinition and Product, with explicit checks on data-model.md CatalogDocument.products, CatalogDocument.categories, CatalogProvenance.sourceType, CatalogProvenance.reviewStatus, Product.name, Product.description and Product.attributes, rejecting duplicate IDs and missing provenance per research.md R2
- [ ] T010 Implement `backend/scripts/seed_catalog.py` loading the validated JSON catalog into PostgreSQL transactionally, reporting version and counts per quickstart.md §3
- [ ] T011 [P] Implement `backend/app/core/config.py` server-only environment configuration (pydantic-settings) and `backend/app/core/validation.py` shared Pydantic schemas per plan.md Security design
- [ ] T012 Implement `backend/app/features/catalog/repository.py` CatalogRepository port with the PostgreSQL implementation in `backend/app/features/catalog/postgres_repository.py` per plan.md Structure Decision
- [ ] T013 [P] Implement `backend/app/lib/telemetry/events.py` and `backend/app/lib/telemetry/logger.py` emitting data-model.md AssistantInteractionEvent to stdout with no raw content by default per research.md R8

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 1 - Discover products with natural language (Priority: P1) 🎯 MVP

**Goal**: Customer states category, characteristics and budget in natural language and receives grounded, catalog-valid recommendations (FR-001, FR-002, FR-003, FR-007)

**Independent Test**: Submit a complete product request through POST /api/v1/assistant/interactions with the fake provider; every returned product exists in the catalog and matches stated requirements; no-match returns explicit relaxations (spec.md US1 acceptance scenarios 1–4)

### Tests for User Story 1

- [ ] T014 [P] [US1] Contract test for POST /api/v1/assistant/interactions in `backend/tests/contract/test_assistant_interaction.py` against contracts/openapi.yaml AssistantInteractionRequest and AssistantInteractionResponse
- [ ] T015 [P] [US1] Integration test for discovery happy path with fake provider in `backend/tests/integration/test_discovery.py` asserting every presented product resolves in the catalog (FR-003)
- [ ] T016 [P] [US1] Integration test for explicit no-match with computed relaxations in `backend/tests/integration/test_no_match.py` asserting no invented products (FR-007, SC-003)
- [ ] T017 [P] [US1] Integration test for empty/unavailable catalog returning unavailable without fabrication in `backend/tests/integration/test_catalog_unavailable.py` (spec.md edge case: empty catalog)

### Implementation for User Story 1

- [ ] T018 [P] [US1] Create `backend/app/features/assistant/domain.py` with types from data-model.md ConversationState, CustomerPreference, PresentedProductReference, Recommendation and AssistantReply
- [ ] T019 [P] [US1] Implement `backend/app/lib/ai/provider.py` provider port and `backend/app/lib/ai/fake_provider.py` deterministic provider per research.md R4
- [ ] T020 [US1] Implement `backend/app/features/assistant/conversation_state.py` validating untrusted client state per data-model.md ConversationState.conversationId, ConversationState.turns, ConversationState.preferences, ConversationState.presentedProducts and ConversationTurn.text (bounds from contracts/openapi.yaml ConversationState)
- [ ] T021 [US1] Implement `backend/app/lib/retrieval/lexical.py` structured eligibility filters and lexical baseline ranking per research.md R3
- [ ] T022 [US1] Implement `backend/app/features/assistant/response_validator.py` catalog hydration and grounding checks: GroundingReference.productId must exist and every displayed value must come from the catalog per data-model.md §4.4 and plan.md Grounding boundary
- [ ] T023 [US1] Implement `backend/app/features/assistant/interaction_service.py` orchestrating preference extraction → retrieval → reply selection → exactly one AssistantInteractionEvent per interaction (FR-014)
- [ ] T024 [US1] Implement POST route `backend/app/api/v1/assistant/interactions.py` with bounded input validation per contracts/openapi.yaml AssistantInteractionRequest
- [ ] T025 [P] [US1] Build chat UI in `frontend/src/app/page.tsx` and `frontend/src/features/assistant/components/` (message list, input, recommendation cards) calling the backend via `frontend/src/lib/api.ts` per spec.md FR-009
- [ ] T026 [US1] Add E2E discovery journey in `tests/e2e/discovery.spec.ts` with fake provider covering spec.md US1 acceptance scenarios 1–4

**Checkpoint**: User Story 1 fully functional and independently testable (MVP)

---

## Phase 4: User Story 2 - Refine criteria across turns (Priority: P2)

**Goal**: Subsequent messages preserve unchanged preferences, replace changed ones, and reload/new conversation resets all context (FR-005, FR-006, FR-013)

**Independent Test**: Multi-turn refinement keeps prior constraints; "New conversation" and full reload both start empty with no persisted storage (spec.md US2 acceptance scenarios 1–6)

### Tests for User Story 2

- [ ] T027 [P] [US2] Unit tests for slot-based preference replacement in `backend/tests/unit/test_conversation_state.py` citing data-model.md CustomerPreference.slot, CustomerPreference.nature, CustomerPreference.sourceTurnId
- [ ] T028 [P] [US2] Integration test for context retention across turns in `backend/tests/integration/test_refinement.py` asserting unchanged requirements survive a refinement (FR-005)
- [ ] T029 [P] [US2] E2E test for new-conversation and full-reload reset with no cookie/localStorage persistence in `tests/e2e/conversation_reset.spec.ts` (FR-013)

### Implementation for User Story 2

- [ ] T030 [US2] Implement same-slot preference replacement in `backend/app/features/assistant/conversation_state.py` citing data-model.md CustomerPreference.value and CustomerPreference.status, leaving unrelated active preferences untouched per data-model.md §3.3 Replacement rule
- [ ] T031 [US2] Wire refinement into `backend/app/features/assistant/interaction_service.py` preserving unchanged requirements when rebuilding the RetrievalQuery per data-model.md RetrievalQuery
- [ ] T032 [US2] Add "New conversation" control in `frontend/src/features/assistant/components/` replacing conversationId and clearing turns, preferences and presentedProducts per data-model.md §9 Conversation transitions

**Checkpoint**: US1 AND US2 both work independently

---

## Phase 5: User Story 5 - Browse the standalone catalog (Priority: P2)

**Goal**: Conventional category/list/detail/filter browsing with explicit empty state and no standalone NL/semantic search (FR-012, FR-009)

**Independent Test**: Navigate categories, list, detail, apply filters; empty combination shows explicit empty state with clear action; catalog endpoints expose no search/query text parameter (spec.md US5 acceptance scenarios 1–5)

### Tests for User Story 5

- [ ] T033 [P] [US5] Contract test asserting GET /api/v1/catalog/products has no free-text/semantic search parameter and returns items: [] on no match in `backend/tests/contract/test_catalog.py` (FR-012)
- [ ] T034 [P] [US5] Integration test for deterministic structured filters and empty result in `backend/tests/integration/test_catalog_filters.py` citing data-model.md Product.price and Product.categoryId
- [ ] T035 [P] [US5] E2E category/list/detail/filter/empty-state journey in `tests/e2e/catalog.spec.ts` covering spec.md US5 acceptance scenarios 1–5 and asserting the full journey completes without authentication (FR-011)

### Implementation for User Story 5

- [ ] T036 [P] [US5] Implement GET routes `backend/app/api/v1/catalog/categories.py` and `backend/app/api/v1/catalog/products.py` per contracts/openapi.yaml
- [ ] T037 [US5] Build catalog pages `frontend/src/app/catalog/page.tsx` and `frontend/src/app/catalog/[productId]/page.tsx` with responsive layout per spec.md FR-009
- [ ] T038 [US5] Implement filter controls and explicit empty state with clear action in `frontend/src/features/catalog/components/` per spec.md US5 scenario 5

**Checkpoint**: All P2 stories independently functional

---

## Phase 6: User Story 3 - Ask about presented products (Priority: P3)

**Goal**: Answer questions about presented/existing products using catalog data only, distinguishing verified from unavailable information and declining out-of-scope requests (FR-004, FR-006, FR-007, FR-010)

**Independent Test**: Catalog-backed question answered from catalog fields; missing evidence returns explicit unavailable; checkout/order/policy question gets transparent decline (spec.md US3 acceptance scenarios 1–5)

### Tests for User Story 3

- [ ] T039 [P] [US3] Integration test for catalog-backed answers and insufficient-evidence decline in `backend/tests/integration/test_qa.py` targeting SC-002 and SC-003 behavior
- [ ] T040 [P] [US3] Integration test for customer-belief vs catalog conflict presenting catalog value as verified in `backend/tests/integration/test_qa_grounding.py` (FR-006)

### Implementation for User Story 3

- [ ] T041 [US3] Implement answer path in `backend/app/features/assistant/interaction_service.py` restricted to products existing in the catalog per data-model.md AssistantReply.kind (`answer`)
- [ ] T042 [US3] Implement transparent out-of-scope responses for checkout/payments/orders/policies in `backend/app/lib/ai/prompts/` and `backend/app/features/assistant/interaction_service.py` (FR-010)
- [ ] T043 [US3] Add E2E Q&A journey in `tests/e2e/qa.spec.ts` covering spec.md US3 acceptance scenarios

**Checkpoint**: Q&A works independently on top of US1

---

## Phase 7: User Story 4 - Present products with stable references (Priority: P3)

**Goal**: Inline name/price/key attributes with ordinal references that stay stable across turns and visibly unavailable fields (FR-008, FR-009)

**Independent Test**: Reference "the first product" resolves to the same catalog product after later turns; missing price renders as unavailable, never invented (spec.md US4 acceptance scenarios 1–5)

### Tests for User Story 4

- [ ] T044 [P] [US4] Unit tests for stable ordinal assignment and resolution in `backend/tests/unit/test_references.py` citing data-model.md PresentedProductReference.ordinal, PresentedProductReference.productId, PresentedProductReference.firstPresentedTurnId

### Implementation for User Story 4

- [ ] T045 [US4] Implement stable PresentedProductReference assignment in `backend/app/features/assistant/conversation_state.py` never reusing or reordering ordinals per data-model.md §3.4
- [ ] T046 [US4] Build inline product presentation cards with matchedAttributes and unavailableFields in `frontend/src/features/assistant/components/` per data-model.md ProductPresentation
- [ ] T047 [US4] Add E2E responsive presentation test across phone/tablet/desktop viewports in `tests/e2e/responsive.spec.ts` (FR-009)

**Checkpoint**: All five user stories independently functional

---

## Phase 8: Evaluation & Hybrid Retrieval

**Purpose**: Versioned evaluation datasets, reproducible reports, and the pgvector semantic layer evaluated against the lexical baseline (research.md R3, R7; Constitution AI-quality gates)

- [ ] T048 [P] Create versioned evaluation fixtures `data/evaluation/{discovery,qa,insufficient-evidence,refinement}.jsonl` with provenance metadata per research.md R7 and plan.md Evaluation and release gates
- [ ] T049 [P] Implement `backend/scripts/generate_embeddings.py` upserting one product_embeddings row per product bound to catalog_version and content_digest, failing closed on mismatch per data-model.md §10 physical rules 1–2
- [ ] T050 Implement `backend/scripts/evaluate.py` producing reports with catalog, dataset, prompt, provider and model versions for SC-001–SC-006, naming SC-004 explicitly as latency distribution under the agreed evaluation workload, per research.md R8 and plan.md Evaluation and release gates
- [ ] T051 Run and record the lexical baseline report in `data/evaluation/reports/baseline.md` BEFORE semantic integration (Constitution: baseline before integration)
- [ ] T052 [P] Implement `backend/app/lib/retrieval/semantic.py` pgvector cosine-similarity candidate retrieval per research.md R3
- [ ] T053 Implement `backend/app/lib/retrieval/hybrid.py` reciprocal-rank fusion with deterministic product-ID tie-breaking per research.md R3
- [ ] T054 Integrate hybrid retrieval behind AI_RETRIEVAL=lexical|hybrid flag in `backend/app/core/config.py` and `backend/app/features/assistant/interaction_service.py`, then re-run evaluation comparing candidate vs baseline (SC-005 report)

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Telemetry completeness, security, delivery evidence and documentation that affect multiple user stories

- [ ] T055 [P] Unit test per-conversation cost aggregation by conversationId in `backend/tests/unit/test_telemetry.py` citing data-model.md AssistantInteractionEvent.conversationId, AssistantInteractionEvent.estimatedCostMinor (FR-014)
- [ ] T056 [P] Integration test asserting exactly one terminal telemetry event on validation, catalog and provider failures in `backend/tests/integration/test_telemetry_failures.py` (FR-014, plan.md Security)
- [ ] T057 [P] Security tests for prompt injection in catalog text and user messages unable to alter instructions or extract data in `backend/tests/integration/test_security.py` (plan.md Security, privacy, and failure behavior)
- [ ] T058 [P] Integration test for provider timeout returning typed provider_unavailable with no partial fabricated content in `backend/tests/integration/test_provider_failure.py` (research.md R4)
- [ ] T059 [P] Implement `backend/scripts/provider_smoke.py` opt-in real-provider smoke test gated by AI_PROVIDER=openai per quickstart.md §8
- [ ] T060 [P] Add CI workflow `.github/workflows/ci.yml` running backend pytest, frontend check and contract tests without hosted credentials (Constitution: CI when available)
- [ ] T061 [P] Write `README.md` covering problem, architecture summary and how to run per portfolio deliverables (planning/ai-engineering-portfolio.md §7)
- [ ] T062 [P] Write ADRs in `docs/adr/` for two-service split, pgvector-in-MVP, provider port and ephemeral conversation state per research.md decisions
- [ ] T063 [P] Create `docs/architecture.md` with component and data-flow diagram per portfolio deliverables (planning/ai-engineering-portfolio.md §7)
- [ ] T064 Run quickstart.md end-to-end validation (install → docker compose → migrate/seed → validate → both services → checks → eval) and fix discrepancies per plan.md Verification Strategy
- [ ] T065 Record final evaluation report with SC-001–SC-006 results and known limitations in `data/evaluation/reports/final.md`; mark SC-005/SC-006 as reports-only until thresholds are approved (spec.md Success Criteria)
- [ ] T066 Record demo evidence (screenshots or clip) in `docs/demo/` per portfolio deliverables (planning/ai-engineering-portfolio.md §7)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundational — MVP
- **US2 (Phase 4)**: Depends on Foundational; extends US1 conversation state — independently testable
- **US5 (Phase 5)**: Depends on Foundational only — fully parallel to US1/US2
- **US3 (Phase 6)**: Depends on US1 answer/reply plumbing
- **US4 (Phase 7)**: Depends on US1 presentation and US2 stable references
- **Evaluation & Hybrid (Phase 8)**: T048–T051 can start after Foundational; T052–T054 require T051 (baseline before integration)
- **Polish (Phase 9)**: Depends on all desired user stories being complete

### User Story Dependencies

- **US1 (P1)**: After Foundational — no dependencies on other stories
- **US2 (P2)**: After Foundational + US1 conversation state — independently testable
- **US5 (P2)**: After Foundational only — no dependencies on US1/US2
- **US3 (P3)**: After US1
- **US4 (P3)**: After US1 (+ US2 for cross-turn reference tests)

### Within Each User Story

- Tests first (must fail before implementation)
- Domain/types → services → routes → UI → E2E
- Story complete before moving to next priority

### Parallel Opportunities

- T002–T005 (Setup) in parallel
- T007, T011, T013 in parallel within Foundational
- T014–T017 (US1 tests) in parallel
- T018–T019 in parallel
- T027–T029 (US2 tests) in parallel
- T033–T035 (US5 tests) and T036 in parallel
- US2 and US5 phases fully parallel to each other after Foundational
- T048–T049, T052 in parallel
- T055–T059, T061–T063 in parallel within Polish

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Contract test for POST /api/v1/assistant/interactions in backend/tests/contract/test_assistant_interaction.py"
Task: "Integration test discovery happy path in backend/tests/integration/test_discovery.py"
Task: "Integration test no-match relaxations in backend/tests/integration/test_no_match.py"
Task: "Integration test empty catalog in backend/tests/integration/test_catalog_unavailable.py"

# Then domain + provider port together:
Task: "Create backend/app/features/assistant/domain.py types"
Task: "Implement backend/app/lib/ai/provider.py + fake_provider.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: US1
4. **STOP and VALIDATE**: Run US1 tests independently; record lexical baseline (T051)
5. Demo if ready

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. US1 → test independently → MVP demo
3. US2 and US5 (parallel) → test independently → demo
4. US3 + US4 → test independently → demo
5. Evaluation & Hybrid retrieval → baseline vs candidate report
6. Polish → full verification, docs, demo evidence

### Sequencing Note

Evaluation phase intentionally follows the lexical baseline-first order mandated by the Constitution: no semantic/hybrid code merges before T051's recorded baseline.

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Tests fail before implementation (TDD)
- Commit after each task or logical group on branch `001-conversational-shopping-assistant`
- Stop at any checkpoint to validate the story independently
- Avoid: vague tasks, same-file conflicts, cross-story dependencies that break independence

## Delivery Log

- **2026-11-25**: T001–T066 implemented and verified (76 pytest + 12 contract, 34 E2E, ruff, frontend lint/typecheck, evaluation reports). Work-unit slices committed on this branch as 8 commits totaling 12,278 authored lines (lockfiles excluded), grouped by feature area (spec → bootstrap → US1/US2 → US5 → US3/US4 → retrieval/evaluation → quality/docs); intermediate commits contain final file states, and HEAD is the fully verified state. Publishing (push/PR) remains a separate human decision.
