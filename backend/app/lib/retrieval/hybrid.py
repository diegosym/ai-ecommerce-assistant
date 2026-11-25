from app.features.assistant.domain import RankedCandidate

RRF_K = 60


def fuse_rankings(
    lexical: list[RankedCandidate],
    semantic: list[RankedCandidate],
    *,
    limit: int,
) -> list[RankedCandidate]:
    """Reciprocal-rank fusion with deterministic product-ID tie-breaking."""
    candidates: dict[str, RankedCandidate] = {}
    scores: dict[str, float] = {}
    for ranking, rank_field in ((lexical, "lexicalRank"), (semantic, "semanticRank")):
        for candidate in ranking:
            existing = candidates.get(candidate.productId)
            if existing is None:
                candidates[candidate.productId] = candidate
                scores[candidate.productId] = 0
            else:
                matched = list(dict.fromkeys([*existing.matchedAttributes, *candidate.matchedAttributes]))
                candidates[candidate.productId] = existing.model_copy(
                    update={
                        "lexicalRank": candidate.lexicalRank or existing.lexicalRank,
                        "semanticRank": candidate.semanticRank or existing.semanticRank,
                        "matchedAttributes": matched,
                    }
                )
            rank = getattr(candidate, rank_field)
            if rank is not None:
                scores[candidate.productId] += 1 / (RRF_K + rank)

    ordered = sorted(candidates, key=lambda product_id: (-scores[product_id], product_id))
    return [
        candidates[product_id].model_copy(update={"hybridRank": index})
        for index, product_id in enumerate(ordered[:limit], start=1)
    ]
