from app.features.assistant.domain import RankedCandidate
from app.lib.retrieval.hybrid import fuse_rankings


def candidate(
    product_id: str,
    *,
    lexical_rank: int | None = None,
    semantic_rank: int | None = None,
) -> RankedCandidate:
    return RankedCandidate(
        productId=product_id,
        lexicalRank=lexical_rank,
        semanticRank=semantic_rank,
        hybridRank=1,
        matchedAttributes=["connectivity"],
    )


def test_reciprocal_rank_fusion_uses_both_rankings() -> None:
    lexical = [candidate("a", lexical_rank=1), candidate("b", lexical_rank=2)]
    semantic = [
        candidate("b", semantic_rank=1),
        candidate("c", semantic_rank=2),
        candidate("a", semantic_rank=3),
    ]

    fused = fuse_rankings(lexical, semantic, limit=3)

    assert [item.productId for item in fused] == ["b", "a", "c"]
    assert fused[0].lexicalRank == 2
    assert fused[0].semanticRank == 1
    assert fused[0].matchedAttributes == ["connectivity"]
    assert [item.hybridRank for item in fused] == [1, 2, 3]


def test_reciprocal_rank_fusion_breaks_equal_scores_by_product_id() -> None:
    fused = fuse_rankings(
        [candidate("b", lexical_rank=1)],
        [candidate("a", semantic_rank=1)],
        limit=2,
    )

    assert [item.productId for item in fused] == ["a", "b"]
