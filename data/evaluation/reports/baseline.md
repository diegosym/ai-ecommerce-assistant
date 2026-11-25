# Lexical baseline evaluation

Generated: `2026-11-25T22:15:22.934844+00:00`

## Reproducibility

- Catalog: `1.0.0`
- Retrieval: `lexical`
- Provider: `fake`
- Chat model: `fake-chat-v1`
- Prompt: `fake-discovery-v1`
- Embedding model: `None`
- Dataset `discovery`: `1.0.0` (18 cases)
- Dataset `qa`: `1.0.0` (16 cases)
- Dataset `insufficient-evidence`: `1.0.0` (16 cases)
- Dataset `refinement`: `1.0.0` (16 cases)

## Headline metrics

| Criterion | Result | Gate / target |
|---|---:|---|
| SC-001 discovery proxy | 100.00% (15/15) | >= 85.00%; measured proxy |
| SC-002 Q&A correctness | 100.00% (16/16) | >= 90.00% |
| SC-003 insufficient evidence | 100.00% (16/16) | >= 95.00% |
| SC-005 Recall@3 | 93.89% | **REPORT-ONLY; threshold deferred** |
| SC-006 refinement | 100.00% (16/16) | **REPORT-ONLY; threshold deferred** |

## SC-004 — Latency distribution under agreed evaluation workload

- Workload: `{"concurrency": 1, "execution": "in-process InteractionService with PostgreSQL and deterministic fake provider", "iterationsPerCase": 1, "requestCountIncludesAllRefinementTurns": true}`
- Requests: 82
- P50: 1.146 ms
- P95: 1.353 ms (target <= 5000 ms)
- Maximum: 1.813 ms

## Case failures

- []

## Limitations and acceptance status

- SC-001 is a catalog-grounded constraint-satisfaction proxy, not human relevance judging.
- SC-005 and SC-006 are reports-only because dataset/methodology approval and thresholds are deferred.
- Datasets are synthetic draft fixtures; no human labeling or approval is claimed.
- Fake deterministic embeddings exercise pgvector mechanics, not hosted semantic quality.
