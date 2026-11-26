# Final evaluation and delivery report

## Reproducibility

Latest local runs used catalog `1.0.0`, dataset version `1.0.0` for all four datasets, provider `fake`, chat model `fake-chat-v1`, prompt `fake-discovery-v1`, and one sequential in-process request per case/turn (82 requests total). Hybrid runs used `fake-embedding-1536-v1` with 1536 dimensions. No hosted calls or credentials were used.

The original lexical baseline was recorded before semantic/hybrid implementation. The latest baseline and candidate runs were repeated during quickstart validation using identical datasets and workload.

## SC-001–SC-006 results

| Criterion | Lexical baseline | Hybrid candidate | Status |
|---|---:|---:|---|
| SC-001 discovery relevance/catalog validity proxy | 100% (15/15) | 100% (15/15) | Measured proxy; target >=85% |
| SC-002 Q&A correctness | 100% (16/16) | 100% (16/16) | Measured; target >=90% |
| SC-003 insufficient-evidence handling | 100% (16/16) | 100% (16/16) | Measured; target >=95% |
| SC-004 P50 latency | 1.146 ms | 3.251 ms | Observed workload |
| SC-004 P95 latency | 1.353 ms | 4.176 ms | Both below 5000 ms target |
| SC-004 maximum latency | 1.813 ms | 6.016 ms | Observed workload |
| SC-005 Recall@3 | 93.89% | 93.89% | >= 90% release gate (pass) |
| SC-006 refinement success | 100% (16/16) | 100% (16/16) | >= 90% release gate (pass) |

SC-004 is the **latency distribution under the agreed evaluation workload**: one iteration per case, concurrency one, in-process `InteractionService` with PostgreSQL and the deterministic fake provider. It excludes HTTP/browser/hosted-provider overhead.

Sources: [baseline](baseline.md), [hybrid](hybrid.md), and [comparison](comparison.md), plus their machine-readable metrics files.

## Additional verification evidence

- Backend: 76 tests passed, including the quickstart `for $150` parser regression.
- Contract-only subset: 12 passed.
- Frontend lint, typecheck, and Vitest command passed (Vitest has no test files and exits 0 by configuration).
- Playwright: 34 executions passed across discovery, reset, catalog, Q&A, and responsive journeys.
- Security: malicious user/catalog text cannot alter instructions or extract data.
- Failure handling: validation/catalog/provider failures emit exactly one terminal event; provider timeout returns typed `provider_unavailable` with no partial content.
- Hosted provider smoke: refused `AI_PROVIDER=fake` as designed; no hosted call was attempted.

## Known limitations

- SC-001 is a catalog constraint-satisfaction proxy, not human relevance judging.
- SC-005 and SC-006 are **reports-only**, not release gates, until thresholds and methodology are approved.
- Datasets are synthetic draft fixtures; no human labeling or approval is claimed.
- Fake embeddings demonstrate pgvector compatibility and ranking mechanics, not hosted semantic quality. Hybrid Recall@3 did not improve over baseline.
- Latency is local/in-process and not a production benchmark.
- Hosted chat/embeddings were not integrated or evaluated; variance for hosted models is therefore not available.
- Frontend Vitest currently has no test files; responsive and functional UI evidence comes from Playwright.
