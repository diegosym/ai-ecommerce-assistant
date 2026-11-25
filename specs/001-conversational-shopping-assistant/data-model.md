# Phase 1 Data Model: Conversational Shopping Assistant

**Feature**: [spec.md](./spec.md)  
**Status**: Design only. Logical entities below map to a PostgreSQL + pgvector persistence model (section 10); conversation state and telemetry remain non-relational (browser memory and stdout events).

## 1. Modeling Principles

- `Product` and `Category` catalog records are the only verified product-fact sources.
- `CustomerPreference` represents a user statement, never a catalog override.
- Conversation data is ephemeral browser state and untrusted when submitted to the server.
- `Recommendation` and `PresentedProductReference` contain product IDs and evidence references; display values are hydrated from the catalog.
- Telemetry is operational metadata, not a conversation-history store.
- JSON examples describe logical shapes; Pydantic schemas (backend) and OpenAPI are the executable contract sources after implementation.

## 2. Catalog Entities

### 2.1 CatalogDocument

| Field | Type | Rules |
|---|---|---|
| `catalogVersion` | string, semantic version | Required; included in telemetry and evaluation reports. |
| `generatedAt` | ISO 8601 timestamp | Required provenance metadata. |
| `provenance` | CatalogProvenance | Required; documents synthetic origin and authorization. |
| `categories` | Category[] | Exactly 4–6 for the completed demonstration catalog. |
| `products` | Product[] | Exactly 100–200 for the completed demonstration catalog. |

### 2.2 CatalogProvenance

| Field | Type | Rules |
|---|---|---|
| `sourceType` | literal `synthetic` | Real customer or production data is forbidden. |
| `method` | string | Describes authored/generated origin without claiming unperformed work. |
| `reviewStatus` | `draft \| reviewed \| approved` | Release evaluation requires approved data. |
| `notes` | string | Documents known limitations and contamination controls. |

### 2.3 Category

| Field | Type | Rules |
|---|---|---|
| `id` | slug string | Unique, stable across compatible catalog versions. |
| `name` | non-empty string | Display label hydrated from catalog. |
| `description` | string | Synthetic category description. |
| `attributeDefinitions` | AttributeDefinition[] | Defines category-relevant filters, labels, types, and units. |

### 2.4 AttributeDefinition

| Field | Type | Rules |
|---|---|---|
| `key` | slug string | Unique within the category. |
| `label` | non-empty string | Display label. |
| `valueType` | `string \| number \| boolean` | Runtime values must match. |
| `unit` | string, optional | Required when a numeric value needs a unit. |
| `filterable` | boolean | Only deterministic structured filters are exposed. |

### 2.5 Product

| Field | Type | Rules |
|---|---|---|
| `id` | slug string | Unique and stable; sole join key for recommendations/references. |
| `name` | non-empty string | Catalog-authored; never accepted from model output. |
| `categoryId` | Category ID | Must resolve to an existing category. |
| `description` | non-empty string | Searchable catalog text; treated as untrusted prompt content. |
| `price` | Money or `null` | `null` renders “unavailable”; never guessed. |
| `attributes` | map of key → scalar or `null` | Keys must be defined for the category; `null` means unavailable. |

A missing attribute key means the attribute is not defined for that product record; a defined key with `null` means its value is unavailable. Both render transparently and neither authorizes inference.

### 2.6 Money

| Field | Type | Rules |
|---|---|---|
| `amountMinor` | non-negative integer | Minor currency units avoid floating-point price arithmetic. |
| `currency` | ISO 4217 code | Initial synthetic catalog uses one documented currency. |

### 2.7 EmbeddingArtifact

| Field | Type | Rules |
|---|---|---|
| `catalogVersion` | string | Must exactly match the loaded catalog. |
| `provider` | string | Recorded integration identity. |
| `modelId` | string | Required for reproducibility. |
| `dimensions` | positive integer | Every vector must match. |
| `contentDigest` | SHA-256 digest | Binds vectors to normalized source text. |
| `vectors` | map of product ID → number[] | IDs must exist in the same catalog. |

Invalid, stale, or incompatible artifacts are not silently used. The explicit generation command rebuilds them.

## 3. Conversation Entities

### 3.1 ConversationState

| Field | Type | Rules |
|---|---|---|
| `conversationId` | UUID | Random ephemeral identifier; not an account/session credential. |
| `createdAt` | ISO 8601 timestamp | Client metadata; server does not treat it as an audit timestamp. |
| `turns` | ConversationTurn[] | Ordered and size-bounded; no cross-reload persistence. |
| `preferences` | CustomerPreference[] | One active preference per logical requirement slot. |
| `presentedProducts` | PresentedProductReference[] | Ordinals are unique, monotonically increasing, and stable. |

`ConversationState` exists in browser memory only. The server validates every submitted field and does not persist it. New conversation and full reload replace the entire object.

### 3.2 ConversationTurn

| Field | Type | Rules |
|---|---|---|
| `turnId` | UUID | Unique within the conversation. |
| `role` | `customer \| assistant` | No system/tool roles cross the public API. |
| `text` | bounded string | User text is untrusted; assistant text contains no unverified product facts. |
| `createdAt` | ISO 8601 timestamp | Ordering is also protected by array position and request validation. |
| `interactionId` | UUID, optional | Links an assistant turn to its telemetry event. |

### 3.3 CustomerPreference

| Field | Type | Rules |
|---|---|---|
| `preferenceId` | UUID | Stable identity within the active conversation. |
| `slot` | `category \| characteristic \| budget \| other` | Defines replacement behavior. |
| `key` | string, optional | Distinguishes multiple characteristic slots, such as connectivity and battery. |
| `nature` | `requirement \| belief` | Only requirements affect eligibility; beliefs never override facts. |
| `value` | validated JSON scalar/object | Budget and category values use normalized forms. |
| `sourceTurnId` | turn UUID | Required attribution to the customer statement. |
| `status` | `active \| replaced` | Replaced preferences remain only in bounded active-conversation history. |

**Replacement rule**: a later customer statement targeting the same logical slot supersedes the earlier active requirement while leaving unrelated preferences unchanged. A statement about a product attribute does not mutate the catalog.

### 3.4 PresentedProductReference

| Field | Type | Rules |
|---|---|---|
| `ordinal` | positive integer | Never reused or reordered within the conversation. |
| `productId` | Product ID | Must resolve at presentation time. |
| `firstPresentedTurnId` | turn UUID | Establishes reference history. |

“The first product” resolves through `ordinal`, not current ranking. If a product disappears from a later catalog version, the assistant says it can no longer verify that product.

## 4. Retrieval and Response Entities

### 4.1 RetrievalQuery

| Field | Type | Rules |
|---|---|---|
| `text` | bounded string | Original customer text, used only as untrusted retrieval input. |
| `requirements` | CustomerPreference[] | Validated active requirements. |
| `limit` | bounded integer | Small recommendation set; upper bound fixed by the API. |

### 4.2 RankedCandidate

| Field | Type | Rules |
|---|---|---|
| `productId` | Product ID | Must exist in the loaded catalog. |
| `lexicalRank` | positive integer or `null` | Baseline evidence; no raw score contract is exposed. |
| `semanticRank` | positive integer or `null` | Absent before semantic integration or without a valid artifact. |
| `hybridRank` | positive integer | Deterministic final order with product-ID tie breaking. |
| `matchedAttributes` | string[] | Only keys supported by the catalog and query. |

### 4.3 Recommendation

| Field | Type | Rules |
|---|---|---|
| `recommendationId` | UUID | Unique within the response. |
| `requestTurnId` | turn UUID | Links to the originating request. |
| `candidates` | RankedCandidate[] | Small relevance-ranked set. |
| `grounding` | GroundingReference[] | One or more for every displayed candidate. |
| `relaxedCriteria` | RelaxationSuggestion[] | Empty unless no exact match or an explicitly supported relaxation flow applies. |

### 4.4 GroundingReference

| Field | Type | Rules |
|---|---|---|
| `productId` | Product ID | Must be present in the response evidence bundle. |
| `fields` | string[] | Allowed catalog fields used for display/answer. |

Every name, price, and attribute rendered from a recommendation must be covered by a grounding reference and hydrated from the server-side catalog.

### 4.5 RelaxationSuggestion

| Field | Type | Rules |
|---|---|---|
| `preferenceId` | UUID | Identifies a real active requirement. |
| `label` | string | Explains which criterion can be relaxed. |
| `resultCount` | non-negative integer | Computed from an actual diagnostic retrieval, not generated. |

## 5. Assistant Response Union

`AssistantReply.kind` is one of:

- `recommendations`: ranked, hydrated product cards and grounding.
- `answer`: catalog-backed answer to a product question.
- `clarification`: asks for missing or ambiguous requirements without silently dropping known ones.
- `no_match`: states that all constraints exclude every product and offers computed relaxations.
- `out_of_scope`: transparently declines excluded capabilities.
- `unavailable`: handles missing evidence, empty/unavailable catalog, removed products, or provider failure.

Every variant contains safe display text. Product-carrying variants also contain `ProductPresentation[]`; non-product variants must not contain product claims.

### 5.1 ProductPresentation

| Field | Type | Rules |
|---|---|---|
| `reference` | PresentedProductReference | Stable within the active conversation. |
| `product` | Product | Server-hydrated current catalog record. |
| `matchedAttributes` | string[] | Explains verified matches only. |
| `unavailableFields` | string[] | Drives explicit unavailable labels. |

## 6. Telemetry Entity

### 6.1 AssistantInteractionEvent

| Field | Type | Rules |
|---|---|---|
| `eventType` | literal `assistant_interaction` | Stable log query key. |
| `interactionId` | UUID | Unique per attempted interaction. |
| `conversationId` | UUID | Ephemeral aggregation key for per-conversation cost. |
| `receivedAt` / `completedAt` | ISO 8601 timestamps | Server-generated. |
| `latencyMs` | non-negative integer | Total latency; stage timings may be nested. |
| `catalogVersion` | string | Required when catalog access is attempted. |
| `provider` / `modelId` | strings or `null` | Includes `fake` where applicable. |
| `promptVersion` | string or `null` | Required for model-backed operations. |
| `inputTokens` / `outputTokens` | non-negative integers or `null` | Unknown values remain null, never zero by assumption. |
| `estimatedCostMinor` / `currency` | number/code or `null` | Estimated, with pricing version; not billing truth. |
| `pricingVersion` | string or `null` | Required when estimated cost is present. |
| `outcome` | response kind or `error` | Supports operational reporting. |
| `errorCode` | typed string or `null` | No stack trace, credentials, prompt, or raw message required. |

Exactly one terminal event is required for every accepted assistant interaction, including validation, catalog, and provider failures. Raw user messages and full prompts are excluded by default.

## 7. Relationships

```text
CatalogDocument 1 ─── * Category
CatalogDocument 1 ─── * Product
Category 1 ─── * Product

ConversationState 1 ─── * ConversationTurn
ConversationState 1 ─── * CustomerPreference
ConversationState 1 ─── * PresentedProductReference
ConversationTurn 1 ─── * CustomerPreference (source attribution)
ConversationTurn 1 ─── 0..1 Recommendation
Recommendation 1 ─── * RankedCandidate
Recommendation 1 ─── * GroundingReference
Product 1 ─── * RankedCandidate / GroundingReference / PresentedProductReference

ConversationState 1 ─── * AssistantInteractionEvent (telemetry-only, not persisted history)
```

## 8. Invariants and Validation

1. Every product/category/reference ID must resolve within the bound catalog or active conversation.
2. Product facts displayed by UI or returned by the assistant must come from server-hydrated catalog records.
3. A belief cannot become a hard filter or overwrite a product attribute.
4. Preference replacement affects only the addressed logical slot.
5. Presented ordinals never change within a conversation.
6. A reload/new conversation creates an empty state and a new conversation ID.
7. No public catalog endpoint accepts semantic or natural-language search text.
8. Catalog provenance, version, and schema are validated before retrieval.
9. Invalid model output cannot bypass unavailable/no-match behavior.
10. Telemetry contains no raw messages by default and supports interaction plus conversation cost measurement.

## 9. State Transitions

### Conversation

```text
[page load] ──► Active(empty)
Active ──customer turn──► Active(preferences/references updated)
Active ──New conversation──► Active(new ID, empty)
Active ──full reload───────► Active(new ID, empty)
Active ──visit ends────────► discarded; no restorable persisted state
```

### Preference

```text
customer statement ──► Active requirement or belief
Active requirement ──same-slot replacement──► Replaced
Active requirement ──new conversation/reload──► discarded
```

### Product reference

```text
eligible catalog product ──presented──► Presented(ordinal assigned)
Presented ──later turns────────────────► Presented(same ordinal)
Presented ──missing from current catalog► Unverifiable; explicit unavailable response
Presented ──new conversation/reload─────► discarded
```

## 10. Physical Persistence Model (PostgreSQL + pgvector)

The portfolio decision (2026-11-25) places relational and vector database design in the MVP. Versioned JSON files remain the reviewable, provenance-carrying source that seeds the database; PostgreSQL is the system of record queried at runtime.

| Table | Purpose | Key columns |
|---|---|---|
| `catalog_metadata` | Current loaded catalog version and provenance | `catalog_version`, `provenance jsonb`, `seeded_at` |
| `categories` | Category records | `id PK`, `name`, `description`, `attribute_definitions jsonb` |
| `products` | Product records (sole facts source) | `id PK`, `name`, `category_id FK`, `description`, `price_minor`, `price_currency`, `attributes jsonb` |
| `product_embeddings` | One vector row per product | `product_id PK/FK`, `embedding vector(d)`, `catalog_version`, `provider`, `model_id`, `content_digest`, `dimensions`, `indexed_at` |

Physical rules:

1. `product_embeddings.catalog_version` must equal `catalog_metadata.catalog_version`; a mismatch fails closed and requires reindexing.
2. Embeddings are derived data: they can always be rebuilt from `products` plus the versioned generation procedure.
3. `ConversationState` and telemetry events are not stored in PostgreSQL (ephemeral browser state; stdout events only).
4. Money stays in integer minor units; `attributes jsonb` is validated by application schemas before write.
5. Evaluation fixtures remain files; they are not mixed into operational tables.
