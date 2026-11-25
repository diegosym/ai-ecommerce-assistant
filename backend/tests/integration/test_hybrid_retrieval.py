from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.core.config import Settings
from app.features.assistant.domain import (
    AssistantInteractionRequest,
    ConversationState,
    CustomerPreference,
    RetrievalQuery,
)
from app.features.assistant.interaction_service import InteractionService
from app.features.catalog.postgres_repository import PostgresCatalogRepository
from app.lib.ai.fake_provider import FakeLanguageModelProvider
from app.lib.retrieval.semantic import rank_semantic_candidates


def requirement() -> CustomerPreference:
    return CustomerPreference(
        preferenceId=uuid4(),
        slot="characteristic",
        key="connectivity",
        nature="requirement",
        value={"key": "connectivity", "operator": "equals", "value": "bluetooth"},
        sourceTurnId=uuid4(),
        status="active",
    )


def test_pgvector_semantic_candidates_keep_structured_eligibility(
    catalog_repository: PostgresCatalogRepository,
) -> None:
    products = catalog_repository.list_products()
    query = RetrievalQuery(
        text="Bluetooth audio for commuting",
        requirements=[requirement()],
        limit=5,
    )

    candidates = rank_semantic_candidates(catalog_repository, products, query)

    assert candidates
    by_id = {product.id: product for product in products}
    assert all("bluetooth" in by_id[item.productId].attributes["connectivity"].lower() for item in candidates)
    assert [item.semanticRank for item in candidates] == list(range(1, len(candidates) + 1))


@pytest.mark.parametrize(
    ("mode", "expected_ids"),
    [
        ("lexical", ["speakers-001", "headphones-001", "speakers-004"]),
        ("hybrid", None),
    ],
)
def test_retrieval_toggle_preserves_baseline_and_hybrid_returns_catalog_valid_products(
    catalog_repository: PostgresCatalogRepository,
    mode: str,
    expected_ids: list[str] | None,
) -> None:
    service = InteractionService(
        repository=catalog_repository,
        provider=FakeLanguageModelProvider(),
        emit_event=lambda _event: None,
        retrieval=mode,
    )
    conversation = ConversationState(
        conversationId=uuid4(),
        createdAt=datetime.now(UTC),
        turns=[],
        preferences=[],
        presentedProducts=[],
    )

    response = service.handle(
        AssistantInteractionRequest(
            conversation=conversation,
            message="Bluetooth audio for commuting",
        )
    )

    assert response.reply.kind == "recommendations"
    assert response.presentations
    products = {product.id: product for product in catalog_repository.list_products()}
    for presentation in response.presentations:
        assert presentation.product == products[presentation.product.id]
        assert "bluetooth" in presentation.product.attributes["connectivity"].lower()
    ids = [presentation.product.id for presentation in response.presentations]
    if expected_ids is not None:
        assert ids == expected_ids


def test_hybrid_flag_is_server_side_configuration() -> None:
    assert Settings(_env_file=None, AI_RETRIEVAL="hybrid").ai_retrieval == "hybrid"
