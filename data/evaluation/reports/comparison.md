# Baseline vs hybrid retrieval comparison

SC-005 (Recall@3) and SC-006 (refinement) are release gates at >= 90%, approved 2026-11-25; deltas below are observations against those targets.

| Metric | Lexical baseline | Hybrid candidate | Delta |
|---|---:|---:|---:|
| SC-001 | 100.00% | 100.00% | +0.00 pp |
| SC-002 | 100.00% | 100.00% | +0.00 pp |
| SC-003 | 100.00% | 100.00% | +0.00 pp |
| SC-005 Recall@3 | 93.89% | 93.89% | +0.00 pp |
| SC-006 | 100.00% | 100.00% | +0.00 pp |
| SC-004 P95 | 1.810 ms | 4.743 ms | +2.933 ms |

Both runs use identical dataset versions and one sequential request per case/turn. Differences are observations, not approved release-gate judgments.
