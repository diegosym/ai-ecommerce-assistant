# Final evaluation and delivery report

## Reproducibility

Latest local runs used catalog `1.0.0`, dataset version `1.0.0` for all four datasets, provider `fake`, chat model `fake-chat-v1`, prompt `fake-discovery-v1`, and one sequential in-process request per case/turn (82 requests total). Retrieval uses real OpenAI `text-embedding-3-small` vectors (1536 dimensions, generated 2026-11-26) stored in PostgreSQL/pgvector; chat stays on the deterministic fake for reproducibility. The hosted path was exercised for real on 2026-11-26: provider smoke passed with `gpt-4o-mini`, and all 120 catalog embeddings were regenerated through the OpenAI API.

The original lexical baseline was recorded before semantic/hybrid implementation. The latest baseline and candidate runs were repeated during quickstart validation using identical datasets and workload.

## SC-001–SC-006 results

| Criterion | Lexical baseline | Hybrid candidate | Status |
|---|---:|---:|---|
| SC-001 discovery relevance/catalog validity proxy | 100% (15/15) | 100% (15/15) | Measured proxy; target >=85% |
| SC-002 Q&A correctness | 100% (16/16) | 100% (16/16) | Measured; target >=90% |
| SC-003 insufficient-evidence handling | 100% (16/16) | 100% (16/16) | Measured; target >=95% |
| SC-004 P50 latency | 1.234 ms | 2.335 ms | Observed workload |
| SC-004 P95 latency | 1.504 ms | 3.087 ms | Both below 5000 ms target |
| SC-004 maximum latency | 3.369 ms | 8.020 ms | Observed workload |
| SC-005 Recall@3 | 93.89% | 93.89% | >= 90% release gate (pass) |
| SC-006 refinement success | 100% (16/16) | 100% (16/16) | >= 90% release gate (pass) |

SC-004 is the **latency distribution under the agreed evaluation workload**: one iteration per case, concurrency one, in-process `InteractionService` with PostgreSQL and the deterministic fake provider. It excludes HTTP/browser/hosted-provider overhead.

Sources: [baseline](baseline.md), [hybrid](hybrid.md), and [comparison](comparison.md), plus their machine-readable metrics files.

## Additional verification evidence

- Backend: 82 tests passed, including the quickstart `for $150` parser regression and the hosted-embedding gate tests.
- Contract-only subset: 12 passed.
- Frontend lint, typecheck, and Vitest command passed (Vitest has no test files and exits 0 by configuration).
- Playwright: 34 executions passed across discovery, reset, catalog, Q&A, and responsive journeys.
- Security: malicious user/catalog text cannot alter instructions or extract data.
- Failure handling: validation/catalog/provider failures emit exactly one terminal event; provider timeout returns typed `provider_unavailable` with no partial content.
- Hosted provider smoke: PASSED on 2026-11-26 with `gpt-4o-mini` (input=20, output=1 tokens) under `AI_PROVIDER=openai`; refusal of `AI_PROVIDER=fake` remains covered by unit tests.

## Known limitations

- SC-001 is a catalog constraint-satisfaction proxy, not human relevance judging.
- SC-005 (Recall@3 >= 90%) and SC-006 (refinement >= 90%) are release gates approved 2026-11-25; the evaluator exits non-zero when either falls below target.
- Datasets are synthetic draft fixtures; no human labeling or approval is claimed.
- With real `text-embedding-3-small` embeddings, hybrid still matches the lexical baseline exactly (Recall@3 93.89% both): on this dataset, structured eligibility plus lexical ranking already saturate top-3, so semantic ranking adds no measurable value. Adopting hybrid as the default is therefore not justified by current evidence.
- Latency is local/in-process and not a production benchmark.
- Hosted chat is smoke-tested but not evaluated end-to-end; hosted-model variance is therefore not available. Full hosted-chat evaluation remains future work.
- Frontend Vitest currently has no test files; responsive and functional UI evidence comes from Playwright.
